# 事务归属上移到请求 seam，service 层不再提交

全仓曾有 45 处 `db.commit()`（service 层 23 处，路由层 22 处），每个 mutating 方法提交自己的事务，导致两个操作无法组合成一个原子动作。我们把事务归属从 module 内部上移到请求 seam：**提交由包在端点上的 `@transactional` 装饰器执行**，位置在处理函数已返回、响应尚未生成之间；`get_db` 的 teardown 退化为「未提交则回滚」的安全网，且永不抛异常。service 方法只 stage，不提交。范围限定在文档/工作流/电子签名路径（`documents.py` / `workflows.py` / `signatures.py` 共 30 个端点，以及 `DocumentService` / `WorkflowService` / `SignatureService` / `AuditService`）。

## Status

accepted

## Considered Options

- **在 `get_db` 或新增的 `get_tx` 依赖的 teardown 里提交**：被否，**依据实测**。在本项目实际安装的 FastAPI 0.141.1 / Starlette 1.6.0 上，yield 依赖的退出代码运行时响应**已经开始发送**：在 teardown 里抛出 `HTTPException`（`BusinessError` 是其子类）不会变成错误响应，而是得到 `RuntimeError: Caught handled exception, but response already started.`。即提交失败**无法报告给客户端**。这与 FastAPI PR #10831 在 0.106 期描述的「退出代码在响应创建后、发送前运行」不同（Starlette 已进入 1.x），因此不能依赖该行为。
- **`@transactional` 装饰器，处理函数返回后立即提交**（采用）：实测三条路径均正确 —— 正常返回 200 且提交；端点体抛 `BusinessError` 时提交被跳过、回滚、返回干净的 400；提交时 `IntegrityError` 被翻译成干净的 409。装饰器写在路由装饰器之下，`functools.wraps` 保留签名以便 FastAPI 正常解析依赖。
- **端点体内显式 `async with uow:` / 显式 `await db.commit()`**：被否。30 处散落的调用点，且提交位置回到人工判断。
- **新增独立的 `get_tx` 依赖自建 session**：被否（该分支随装饰器方案一并消失）。FastAPI 的依赖缓存按 callable，而 `get_current_user` 依赖 `get_db`，自建会使一个写请求出现两个 session、两个事务并使连接占用翻倍。装饰器方案下 session 仍只由 `get_db` 提供，此问题不复存在。
- **迁移期让 service 的 commit 变成「已在事务中则空操作」**：被否。会使「谁提交」在迁移期出现两种语义并存，恰是要消灭的那类知识，且此类临时抽象很少真被删除。

## Consequences

- 提交发生在**响应生成之前**，因此提交失败可以被翻译为业务错误返回给客户端。任何异常（含 `BusinessError`、`PermissionDeniedError`）一律跳过提交并回滚。此前 service 提前提交，抛在后半段的业务错误可能留下已落库的前半段，该问题随之消失。
- `IntegrityError` 由装饰器兜底翻译为 409；但已知的唯一约束仍必须在 service 内显式预检（如 `create_urs_reference` 的先查重后插），兜底翻译不作为常规校验手段。
- service 层 18 处 `await db.refresh(...)` 改为 flush 后读或删除。`expire_on_commit=False` 保证对象在提交前后均可读。
- 忘记加装饰器的后果是静默不落库，因此强制手段必须同时覆盖两件事：以 AST 测试禁止 `app/services/**` 内出现 `.commit(` / `.rollback(`，**并**断言范围内三个路由的每个 `post` / `put` / `delete` 端点都带有 `@transactional`。前者附一份递减白名单，从 23 处已知例外起步，随迁移逐条划除，终态仅保留 savepoint 一处；迁移进度因此成为 CI 中一个可读的数字。`ProjectService` 的 5 处提交（服务范围外的 `projects.py`，但可从范围内的只读权限检查路径抵达）在白名单上作为显式已知债务保留。
- `create_urs_item` 的 `item_code` 冲突重试改用 savepoint (`begin_nested`) 包裹。原实现在 `IntegrityError` 时直接 `rollback()`，单事务下会抹掉整个请求已暂存的工作。**已实测**：aiosqlite（SQLite 3.50.4）+ SQLAlchemy 2.0.53 上 savepoint 语义正确，内层冲突回滚后外层暂存的工作存活、重试结果落库。
- `AuditService.log` 仅去掉内部的 `commit()` / `refresh()`，interface 一字不改。它的 11 个参数、自由文本 action 词表、以及 6 处就地构造 `AuditLog` 的重复留待后续处理 —— 那些重复正是因本决策未落地才存在，落地后它们成为没有理由存在的重复。
- 关闭一个 ADR-0003 的实际缺口。**已实测**：令 `PUT /documents/{id}` 的首次 `audit.log` 失败后，文档标题已落库为新值而 `UPDATE` 审计行数为 0 —— service 先提交文档变更，随后每个变更字段各调一次自行提交的 `audit.log`，最多 4 个事务。
- 迁移按「端点 + 其独占的 service 方法」成对进行。前提事实：三个路由中每个会写的 service 方法恰有唯一端点调用者，故摘除单个方法的提交不会波及其他端点。第一刀只做 `PUT /documents/{id}`，但穿透全层：装饰器、AST 与装饰器覆盖断言、错误契约、以及一个注入失败的测试同时立起。
- 该注入测试**会被故意反转**：迁移前断言「文档已改、审计缺失」以证明缺口存在，迁移后断言「文档未改、审计未写」。其意图须在测试名与注释中写明。
- 测试新增与 seam 同边界的 fixture（结束时回滚），直接调 service 的测试改为断言**未提交**状态，从而能在一个事务内同时断言状态跃迁与审计轨迹写入。此前这只能通过 `GET /api/v1/audit-logs` 事后反查间接验证。
- `seed_rbac.py` / `seed_dict.py` 在请求生命周期之外自管事务，不受影响；`admin.py` / `auth.py` / `dictionary.py` / `systems.py` 四个路由内的 22 处提交不在范围内 —— 它们没有 service 层，改动它们等于顺带补建 service 层，属于另一件事。
- 本决策的机制依赖具体版本行为，而 `requirements.txt` 全为 `>=` 开区间且无 lock 文件。装饰器方案不依赖 teardown 的报错能力，因此对版本漂移不敏感；但若将来改回依赖 teardown，必须重新实测响应是否已开始发送。
