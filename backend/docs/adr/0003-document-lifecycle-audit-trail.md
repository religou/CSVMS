# 文档全生命周期审计轨迹

为满足 21 CFR Part 11 §11.10(e) 的完整审计要求，文档从起草到作废的**每一次状态跃迁**都写入系统级 `AuditLog`：创建、编辑、提交、审核通过、批准通过、拒绝、退回、撤回、电子签名、发起变更（破坏已批准状态）。所有此类事件统一记在 `resource_type="document"`、`resource_id=document_id` 下，使一份文档的完整历史汇聚在它自己的审计轨迹中。

## Status

accepted

## Considered Options

- **工作流事件记在 `resource_type="workflow"`**：被否——按资源查看时不会出现在文档审计轨迹里，割裂了文档的完整历史。
- **统一记在文档下**（采用）：贯穿全生命周期的记录集中可查。

## Consequences

- 审计与状态变更**同一事务**写入（service 层），杜绝「状态变了但审计漏记」。submit/return/withdraw/revise 端点透传 `ip_address`。
- 「审核」与「批准」在审计中区分：审核步通过 → `action="REVIEW"`；批准步通过 → `action="APPROVE"`。
- 发起变更显式记录状态破坏：`action="REVISE"`、`field_changed="status"`、`old_value="approved"`、`new_value="draft"`、`reason=变更原因`。同时对被取代版本的每条电子签名各写一条 `action="SIGNATURE_VOID"`（`field_changed="signature"`），表明其对当前文档不再生效（签名记录本身不销毁）。
- 规范 action 词表：`CREATE/UPDATE/DELETE/SUBMIT/REVIEW/APPROVE/REJECT/RETURN/WITHDRAW/SIGN/REVISE/SIGNATURE_VOID`（自由文本 String，非枚举）。
- `WorkflowAction`（工作流内部流水）与 `AuditLog`（系统级审计轨迹）并存，用途不同均保留。
- 工作流类事件把 `workflow_id`（及电子签名 id）备注在 `resource_name` 以便回溯。
