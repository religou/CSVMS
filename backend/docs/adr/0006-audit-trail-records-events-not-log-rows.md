# 审计轨迹的写入侧接收「生命周期事件」，不再接收日志行

`AuditService.log` 曾是一个 11 参数的通用日志写入器，而它的 8 个调用点全部传 `resource_type="document"`；因为它自行提交（见 ADR-0004），两个真正改状态的 service 干脆绕开它，就地构造了 6 处 `AuditLog(...)`。现在写入侧只有一个入口 `record(event, actor, ip_address)`：调用方描述**发生了什么**，怎么落成审计行由本 module 决定。`resource_type`、操作人用户名解析、`resource_name` 文案、审核步与批准步的区分、以及一次事件展开成多行（字段变更、签名失效）都收在 interface 之后。全仓 `AuditLog(...)` 的构造点从 8 处收到 1 处。

## Status

accepted

## Considered Options

- **保留通用 `log()`，在上面加一层文档专用 facade**：被否。留下两条路，而「有两条路可走」正是那 6 处绕开 `AuditService` 的直接原因。
- **每类事件一个具名方法**（`record_submitted` / `record_approved` / …）：被否。把 interface 撑到十余个入口，正好是加深的反面。
- **一个封闭枚举加一堆可选参数**：被否，那就是绕回原来的 11 参数 interface。
- **事件用枚举加自由字典 `detail`**：被否，把编译期检查换成运行期约定。
- **每个事件一个小数据类构成封闭联合，`record(event)` 单参数**（采用）：事件自己知道对应的动作词与文案；`_Row` 是事件展开后的中间产物，对调用方不可见。
- **调用方循环调用 `record` 写多行** vs **事件自己表达「N 条」**：采用后者。`FieldsChanged(changes=...)` 与 `SignaturesVoided(signatures=...)` 各传一次，由 module 展开。这消掉了两处「正确性漏到调用方」的循环，其中 `PUT /documents/{id}` 那处尤其明显 —— 端点原先必须记得先读旧值、记得逐字段比较、记得每个字段各写一条。
- **把读侧 `query` 拆成独立 module**：被否，作为明确的非目标。写侧是深 module、读侧是查询构造器，共处一类的内聚性确实不高；但按删除测试，单独抽一个读 module 只会把 `query` 挪个地方（它唯一的调用者是 `audit.py` 的两个读端点），并不集中复杂度。
- **动作词表加数据库层枚举约束**：被否，需要迁移且直接推翻 ADR-0003。

## Consequences

- **`AuditAction` 成为 Python 侧的封闭词表，数据库列仍是 `String`。** ADR-0003 的「自由文本 String，非枚举」在此读作**列类型**的决策 —— 目的是让词表演进不必迁移。本枚举只约束写入侧，因此免迁移的性质保留，同时拼错 action 变成类型错误。本 ADR 不修改 ADR-0003，只记录这个读法，以免后人以为决策被悄悄推翻；若认定原意是「连 Python 侧也不要枚举」，则应改 ADR-0003 而不是本条。
- 修掉了两份互相冲突的词表。`AuditLog.action` 的列注释原先写 `CREATE/UPDATE/DELETE/LOGIN/LOGOUT/SIGN/APPROVE/REJECT`，ADR-0003 写的是另外 12 个词，而两份都不等于实际写出的 8 种。`LOGIN` / `LOGOUT` 是声明了却无人产生的死词，现已移除；有测试断言词表中不允许存在死词。
- **差异计算移入 `DocumentService.update_document`**：文档知道自己哪些字段变了，端点不必先 `get_document` 取旧值再逐字段比较。「传入同值不产生审计行」这个行为本身没有改变（旧实现也做同样的比较），改变的是这段比较逻辑的归属 —— 它从端点搬进了文档 module，端点因此不再需要知道审计的存在。
- 补齐了文档域的审计空白：起草、删除、URS 条目的增删、URS 引用的增删此前一条审计都不写。**另加一项超出原定范围的事件**：URS 条目描述的修改。原范围只列了「增删」，但需求原文被改写而无痕，在 Part 11 语境下比增删漏记更严重，故一并补上。
- 审计写入的 `ip_address` 由端点透传，因此 `documents.py` 的 9 个写端点都增加了 `request: Request` 参数。这是一处**已知的重复**：每个端点都必须记得传 `ip_address`，仍是「正确性漏到调用方」的形状。彻底消除它需要请求作用域上下文，属独立议题，不在本次范围。
- 同一事件展开出的多行**共用一个时间戳**，以便从审计轨迹还原「这是一次操作」而非若干次。有测试断言这一点。
- `resource_type` 不再出现在写入侧 interface（读侧 `query` 保留，`audit.py` 的两个读端点需要它）。按「一个 adapter 只是假想的 seam」，将来真要 user / system 级审计时再开第二个方法，而不是现在预留参数。
- 漏记由 `tests/test_audit_trail.py` 的清单守住：范围内每个写端点必须声明它产生哪些 `AuditAction`（刻意不产生的登记为空集合并写明理由），新增写端点未登记即报红。已验证该清单不是恒绿的装饰 —— 移除起草的审计写入、或向词表加一个无人产生的死词，都会被对应测试逮住。
- **范围外的审计空白登记为显式债务**（`KNOWN_AUDIT_GAPS`）：`auth.py` 的登录登出注册、`admin.py` 的建删用户与改角色重置密码、`dictionary.py`、`systems.py`、`projects.py`、以及工作流模板的增改，均无审计。补它们需要 `resource_type != "document"`，且这些路由没有 service 层 —— 与 ADR-0004 把它们划在事务 seam 范围外是同一个理由。
- `CONTEXT.md` 的「审计轨迹」条目更新：原先枚举的事件列表已不完整，现补上删除与 URS 条目/引用的变更。
