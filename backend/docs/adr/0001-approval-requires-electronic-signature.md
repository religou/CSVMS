# 审批动作强制绑定电子签名（合并为单原子事务）

为满足 21 CFR Part 11，工作流中任何推进或否决状态的决策动作（审核步/批准步的「通过」、任意步的「拒绝」）都必须伴随一次电子签名。我们将签名合并进 `POST /workflows/{id}/approve` 与 `/reject` 接口：请求体新增 `password`，后端在**同一数据库事务**内完成「密码重认证 → 写入电子签名 → 变更工作流/步骤/文档状态 → 写入系统审计日志」，任一步失败整体回滚。

## Status

accepted

## Considered Options

- **两步顺序调用**（先 `POST /signatures` 再 `POST /workflows/{id}/approve`）：被否。两个独立请求会产生「签了名但批准失败」或「批准了却没签名」的中间态，破坏合规要求的强一致性。
- **合并单接口、单事务**（采用）：签名与状态变更原子化，杜绝脏数据。

## Consequences

- `WorkflowActionRequest` 新增必填字段 `password`；用户名不进请求体，后端以当前登录用户身份 (`current_user`) 作为签名标识组件，密码为即时重新输入组件（满足 §11.200 双组件要求）。
- 签名含义 (meaning) 由后端按 `step_type` + 动作自动生成，用户不可改；与用户填写的审批意见 (comment) 分开存储。
- 每个决策动作除 `WorkflowAction`（内部流水）外，额外写一条系统级 `AuditLog`（审计轨迹）。
- 密码错误时返回错误、工作流状态不变，允许重试。
