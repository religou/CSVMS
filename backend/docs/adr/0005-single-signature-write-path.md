# 电子签名只有一条写入路径，签名含义一律由系统推导

`WorkflowService._record_signature_and_audit` 曾完整重写了一遍 `SignatureService.sign`：同样的密码重认证、同样的 `SHA-256(内容 + 签名人 + 时间戳)`、同样十个字段的 `ElectronicSignature` 构造。这份重复唯一的理由是提交边界（前者只 flush、后者自行 commit），而 ADR-0004 已经移除了这个理由。现在 `SignatureService` 是写入一条电子签名的唯一实现，对外只有两个入口：`sign_for_step`（审批动作产生的签名，含义由步骤类型与动作推导）与 `sign_standalone`（工作流之外的独立签名，含义由签署类型推导）。两者都**不接受调用方指定签名含义**。

## Status

accepted

## Considered Options

- **删除 `POST /signatures` 与 `SignatureService.sign`**：被否。按删除测试它确实该删 —— 前端 `signatureService` 定义了但全仓零引用，唯一的调用者是测试，删掉复杂度不会在别处重现。但三处独立证据指向有人打算用它：`ElectronicSignature.meaning` 的列注释写着「（审核/批准/起草）」、测试里真的在签「起草」、前端留了 `sign` 存根。删掉一个 Part 11 的签名入口比保留它更难回退，故保留。
- **保留端点，但把自由文本含义换成封闭的签署类型**（采用）：保住能力，同时堵掉「客户端可自拟法律语义」这个洞。
- **新开第三个 module 供两边调用** / **只把哈希与构造抽成 helper**：被否。前者是加法，而 `SignatureService` 本就是这个概念的命名归属；后者会留下两套编排，含义推导仍有两处。
- **单一入口 `sign(purpose, ...)`**：被否。工作流路径需要先把「步骤类型 + 动作」映射成 purpose，推导逻辑又漏回调用方 —— 那正是本决策要消除的东西。两个具名方法的 interface 反而更窄。
- **`sign_standalone` 也允许绑定工作流步骤**：被否。让调用方把签名挂到任意步骤上是一个伪造入口；需要绑定步骤的签名一律由审批动作产生。
- **保留 `SignatureRequest.username` 作为额外确认**：被否，且它违背 ADR-0001 已判过的取舍（「用户名不进请求体，后端以当前登录用户身份作为签名标识组件」）。让客户端提交身份标识是给冒签开口，前端 `SignatureModal` 把签名人输入框设为 disabled、注释写「防止冒签」，正是同一个判断。
- **一次性给全签署类型（起草/见证/培训确认…）**：被否。签名含义是写进签署记录的法律文本，没有调用者能证明措辞是否正确，猜错的成本高于晚加的成本。枚举先只放「起草」，加一个成员是一行。

## Consequences

- **破坏性 API 变更**：`SignatureRequest` 去掉 `username`、`meaning`、`workflow_id`、`workflow_step_id`，新增必填的 `signature_type`。非法或缺失的签署类型返回 422。客户端塞进来的 `meaning` / `username` 被忽略而非报错（Pydantic 默认丢弃未声明字段），已有测试断言其不生效。影响面可控：唯一的真实调用者是测试，前端调用点是死代码。
- **签名含义的措辞由测试钉死，改动必须刻意。** 四句已核准措辞（三句工作流 + 「起草」的「我起草了此文档，内容由本人编制」）以字面量清单登记在 `tests/test_signatures.py::APPROVED_MEANING_WORDING`，并有测试断言实现与之逐字一致。这份重复是故意的：它让法律文本的改动无法静默发生，报红即意味着有人改了签署记录中的措辞，需经质量负责人重新核准后同步更新清单。其余测试都引用实现里的常量，因此一次措辞变更只打红这一个测试。新增签署类型若未登记核准措辞，同样报红。
- 解决了一处领域模型冲突：CONTEXT.md 原先说签名含义「由系统按步骤类型与动作自动生成」，而 `StepType` 只有 `REVIEW` / `APPROVE`，**起草是任何步骤类型都产生不出来的含义**。现在术语表记录两个来源（工作流步骤、签署类型），并新增「签署类型」一词。
- `WorkflowService` 删除 `_verify_signer` 与 `_signature_meaning`，`_record_signature_and_audit` 收缩为只写审计轨迹的 `_add_step_audit`；`hashlib`、`verify_password` 的依赖随之消失。审批路径的审计轨迹仍归属文档（ADR-0003）不变。
- 签名**先于状态变更**写入：`approve_step` / `reject_step` 在改动步骤状态之前调用 `sign_for_step`，因此密码错误不会留下任何改动。ADR-0004 的单事务本已保证回滚，但保持早失败让失败路径不依赖回滚正确性。
- `ElectronicSignature` 构造时直接赋关系对象（`user=`、`document=`）而非仅赋外键，使 `signature.user` / `.document` 在本事务内即可读 —— 响应构造与审计轨迹不再触发异步 lazy load，也不再需要 `refresh()`。
- `verify_signature` 仍只读取存储的 `is_valid`，**不重算内容哈希**，因此 ADR-0002 为 `is_valid` 保留的「哈希校验失败」场景目前没有任何代码会触发。刻意不在本次处理：重算先要回答「拿哪一份内容算」（活动文档还是 `DocumentVersion` 快照），那是压在 ADR-0002 上的独立议题。已在 `verify_signature` 的 docstring 中写明。
- 签名含义词表由三个测试守住，各管一件事：**路由**（哪个分支选哪一句，含「拒绝优先于步骤类型」）、**措辞**（与已核准文本逐字一致）、**覆盖**（枚举每个成员都有经核准的措辞）。把路由与措辞分开，是为了让措辞变更的报红范围恰好等于一个测试。
