# 最终报告：系统表单新增「符合法规」字段

日期：2026-10-12。评审结论：APPROVED。**没有提交任何代码**：所有改动都还是工作区里未提交（modified / untracked）的状态。

## 1. 缺失的 Alembic 迁移 20260708_0001 及阻塞的解决

**原因**：数据库的 `alembic_version` 是 `20260708_0001`，但代码里的迁移链只到 `20260705_0001`。实际缺了三个迁移：0706、0707、0708。它们和另外 60 个文件一起在提交 `332a272`（「修改了审批流」）里加入。后来一次 `git reset HEAD~1` 把这个提交从 `main` 上移除了。数据库在 reset 之前已经跑过这三个迁移。`332a272` 现在是一个悬空提交（dangling commit），对象还在。

**三个迁移各自做了什么**：
- `20260706_0001`：只改数据。补全 `project_role` 字典项的 `permission_codes`，upsert `permissions` 种子数据，并给 `admin` 角色补上缺少的权限。它依赖 `app/core/permission_catalog.py`，这个文件也被 reset 删掉了。downgrade 不做任何事。
- `20260707_0001`：只改数据。`users.password_changed_at` 为 NULL 时，用 `COALESCE(updated_at, created_at)` 回填。downgrade 不做任何事。
- `20260708_0001`：给 `workflow_steps` 加 `project_role VARCHAR(50) NULL`。对状态为 IN_PROGRESS 或 PENDING 的流程，按 `workflow_template_steps` 回填这一列。downgrade 删除这一列。

**解决方式**：用 `git restore --source=332a272` 原样恢复了 4 个文件：上面 3 个迁移，加上 `app/core/permission_catalog.py`。恢复前先把孤立的 `.pyc` 反汇编，确认源码和字节码一致。没有执行 stamp，没有改 `alembic_version`，也没有删除任何东西。恢复后，`alembic heads` 和 `current` 都返回 `20260708_0001 (head)`，`upgrade head` 不做任何改动。

**待用户决定（本次未处理）**：`332a272` 里还有一批应用代码不在 `main` 上，比如审批流、邀请、通知、首次登录强制改密码。现在能正常运行，是因为那些多出来的列都允许为空。如果以后可能用到这个提交，建议先执行 `git branch rescue/332a272 332a272`。否则 git 回收悬空对象时它会丢失。

## 2. 写入的「法规」字典项（category `regulation`，共 18 项）

| sort | code | 名称 | 核实来源 |
|---|---|---|---|
| 10 | `fda_21cfr_part11` | FDA 21 CFR Part 11 电子记录与电子签名 | eCFR |
| 20 | `fda_21cfr_part210_211` | FDA 21 CFR Parts 210/211 药品 cGMP | eCFR |
| 30 | `fda_21cfr_part58` | FDA 21 CFR Part 58 GLP | eCFR |
| 40 | `fda_21cfr_part820_qmsr` | FDA 21 CFR Part 820 QMSR（2026-02-02 生效） | eCFR；Federal Register 2024-01709、2025-21955 |
| 50 | `fda_csa_guidance` | FDA CSA 计算机软件保证指南（2025-09 定稿） | Federal Register 2025-18468 |
| 60 | `fda_data_integrity_cgmp` | FDA 数据完整性问答指南（2018-12） | Federal Register 2018-26957 |
| 70 | `eu_gmp_annex11` | EU GMP 附录 11 计算机化系统（2011 版现行，修订稿已征求意见） | EudraLex Vol.4；EC 征求意见列表 |
| 80 | `eu_gmp_annex15` | EU GMP 附录 15 确认与验证 | EudraLex Vol.4 |
| 90 | `ema_ct_computerised_systems` | EMA 临床试验计算机化系统与电子数据指南 | EMA 指南 PDF |
| 100 | `ich_e6_r3` | ICH E6(R3) GCP | EMA ICH E6 页面 |
| 110 | `ich_q9_r1` | ICH Q9(R1) 质量风险管理 | EMA ICH Q9 页面 |
| 120 | `pics_pi_011_3` | PIC/S PI 011-3 GxP 计算机化系统良好实践 | PIC/S 出版物页面（日期未核实） |
| 130 | `pics_pi_041_1` | PIC/S PI 041-1 数据管理与完整性 | PIC/S 出版物页面（日期未核实） |
| 140 | `mhra_gxp_data_integrity` | MHRA GxP 数据完整性指南 | GOV.UK |
| 150 | `who_trs1033_annex4` | WHO TRS 1033 附录 4 数据完整性 | who.int |
| 160 | `nmpa_gmp_annex_cs` | NMPA GMP 附录《计算机化系统》 | **未在线核实**（nmpa.gov.cn 返回 HTTP 412，内容来自已有知识） |
| 170 | `nmpa_gcp_2020` | NMPA《药物临床试验质量管理规范》2020 年第 57 号公告 | gov.cn |
| 180 | `ispe_gamp5_2nd` | ISPE GAMP® 5 第二版（行业指南，不是法规） | **未在线核实**（ispe.org 返回 HTTP 403） |

完整的 label 和 description 见 `regulation-items.md`。

## 3. 改动的文件

后端：
- `alembic/versions/20261012_0001_add_regulations_to_systems.py`（新增）：给 `systems` 加 `regulations` JSON 列（可空），并幂等写入 `regulation` 分类和 18 个字典项。可以 downgrade。
- `alembic/versions/20260706_0001_…`、`20260707_0001_…`、`20260708_0001_…`（从 `332a272` 恢复）：补全迁移链。
- `app/core/permission_catalog.py`（从 `332a272` 恢复）：0706 迁移导入了它。
- `app/scripts/seed_dict.py`：`SEED_DATA` 加入同样的 `regulation` 分类和 18 项。
- `app/models/system.py`：`System` 模型新增 `regulations` JSON 列。
- `app/schemas/system.py`：Create/Update 新增可选的 `regulations: list[str]`，Response 默认返回 `[]`。
- `app/api/v1/systems.py`：`_system_response` 返回 `regulations or []`，NULL 会转成空数组。没有单独的 service 层改动。
- `tests/test_systems.py`（新增）：测试创建和更新的往返，以及 PATCH 的语义。
- `tests/test_dictionary.py`：测试种子数据会创建法规分类，并检查迁移快照和 `SEED_DATA` 一致。

前端：
- `src/services/systems.ts`：`SystemItem` 和 Create/Update 类型新增 `regulations`。
- `src/pages/Systems/index.tsx`：在 GxP/GAMP5 和「系统描述」之间新增「符合法规」多选，选项来自 `useDictItems('regulation')`，编辑时回填已有值。这个文件也包含之前几项请求的改动：版本号移到「系统名称」下、「供应商」上面；「供应商」改名为「供应商名称」。
- `src/pages/Systems/index.test.tsx`（新增）：测试选项加载、字段位置、编辑回填和保存时的请求数据。
- `src/pages/Admin/DictManagement.tsx`：新增 `CATEGORY_DISPLAY_ORDER`。这是之前「系统角色」放到「文档类型」和「项目角色」之间的请求。这次把 `regulation` 加到最后，所以「法规」页签排在末尾。

## 4. 验证结果

- **Alembic**：`upgrade head` 通过（`20260708_0001 -> 20261012_0001`），只有一个 head。`downgrade -1` 再 `upgrade head` 的往返也通过。先 stamp 到 `20260708_0001` 再重新 upgrade，没有报错，也没有产生重复数据。数据库检查：`systems.regulations` 是可空 JSON 列；`regulation` 分类有 1 条；字典项 18 条，全部启用；已有系统的这一列仍为 NULL。
- **后端 pytest**：`tests/test_systems.py` 和 `tests/test_dictionary.py` 共 12 个测试通过。`-k "system or dict"` 共 25 个通过、190 个跳过。全量测试在 10 分钟内没有跑完，所以没有全量结果。
- **前端 tsc**：共 24 个错误，全部在 7 个原有文件里，和 `plan.md` 记录的基线一致。没有新增错误，改动的文件里没有错误。
- **前端 vitest**：Systems、DictManagement、Projects 共 3 个文件 4 个测试通过。
- **API 往返测试**（在运行中的开发服务器上进行）：
  - 字典接口返回 18 项。
  - POST 带 `["fda_21cfr_part11"]`，返回值和传入一致。
  - PATCH 成两项后，GET 返回一致。
  - 原有系统返回 `regulations: []`。
  - 测试用的系统已删除。
- **UI**：没有可用的浏览器工具。字段位置和编辑回填由 vitest 的 DOM 测试覆盖。Vite 返回的代码里包含这个字段。字典管理页「法规」页签排在最后这一点，既没有人工检查，也没有测试。
- **评审**：APPROVED。有 4 个不阻塞的问题：
  1. downgrade 会删除管理员手动新增的法规项和已保存的选择。
  2. 后端不检查 code 是否存在于字典中。
  3. 被禁用的字典项在编辑时显示为原始 code。
  4. 法规页签的顺序没有测试。

## 提交状态

**没有提交任何代码。** 本步骤也没有改代码。所有改动（包括之前几项请求的界面调整和恢复的 4 个文件）都在工作区里等待用户审阅后提交。
