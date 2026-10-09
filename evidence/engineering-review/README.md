# Cocos Android 工程规划审核

2026-10-09。设计已获批，工程实现尚未开始。本页把获批设计落实为原 Standard 流程的具体工程规划；其他四个补充验证分支继续保留。

**本次拟执行：发布已批准的设计包，在隔离 Cocos 工程实现菜单，再在两台专用 Android 模拟器完成各 16 项验证。** 工程公开上传和真实 CI 待可运行源码、工作流及上传清单准备好后，再提交具体审核。

## 已确认输入

| 输入 | 固定内容 |
| --- | --- |
| 设计 | `UI-OD-COCOS-MENU/U001`，D=`c0156a9bbe28a80ae39f55a93132c459e3476190`；[原设计审核](../open-design-review/approval/reviewed-README.md) |
| 人工批准 | A=`a5b141b41e194026841602967f3d4efe81dfb431`；[原话、决定及恢复](../open-design-review/approval/README.md) |
| UI 权威 | 沿用 `liam-i/ui-harness-pilot-design-20261008` 的 `main`；逻辑身份、policy 和完整历史不另建一套 |
| 工程起点 | Cocos Creator 3.8.8 的现有 `empty-2d` 模板；[Android 空场景构建和运行证据](../cocos-android-preflight/native-artifact-and-runtime.json)只证明工具链前提 |
| 独立验收依据 | [已审 C01–C16](../open-design-review/package/expected-copy.json)，两设备共 32 项；七种画面状态、字号／方向／生命周期和资源义务不删减 |
| 工程路径 | 新建隔离目录 `/private/tmp/ui-reconciliation-20261009-kd2a3glf/cocos-menu`，功能分支 `codex/cocos-menu-supplementary`；现有 preflight 及失败目录保留 |

完整 Git 引用、源码观察及待发布文件见[固定输入](inputs.json)。本次不使用新的 Version Requirement Layer；原 Standard Change 是唯一业务任务载体。

本页、四份 Change 文件和固定输入按[审阅清单](review-manifest.json)保存摘要。后续审批绑定这一组内容；如果实质范围变化，先更新原规划并重新审阅，不在执行中换成另一份计划。

## 实施内容

1. 将已准备好的设计提交 S/P/D/闭包/A 以普通快进发布到上述 UI 权威；先核对远端基线。只新增[发布清单](inputs.json)中的文件，旧包与旧决定不变。若远端已有并发变化，保留现场并核对，不强推、不回退权威。
2. 在隔离工程固定原任务输入，恢复共同工具及设计对象；执行真正的 current `propose` 检查。通过后，将本页的 [Proposal](change/proposal.md)、[Spec](change/specs/cocos-menu/spec.md)、[Design](change/design.md)、[Tasks](change/tasks.md)原样放入 `openspec/changes/consume-approved-cocos-menu/`。本页目前是完整规划审阅副本，没有假称业务 Propose 已通过。
3. 保存本次真实工程审阅／Apply 请求，固定 Proposal 与 binding。绑定引用真实批准 A；行为分母来自 Spec，UI 状态及允许差异来自已审 D。固定引用所需的本地提交属于交接记账，不改受审语义。开始前再执行 current `start` 检查；恢复时执行 `resume`，不得用本地历史通过替代远端 current。
4. 按唯一 Tasks 实现 Scene、状态行为、素材导入、Android 系统交互及只读测试观察。行为任务按原 Apply/TDD；规划没有要求重做设计或另建框架。
5. 构建实际 APK，执行两设备各 16 项，保存截图、资源映射、原始断言与退出码。修复实现偏差并定向复验；设计或验收义务若确需变化，先说明冲突，不能改获批 D 或降低通过条件。
6. 准备实际 CI 候选后提交远程操作审核；真实 CI 正常／失败／恢复完成后，展示运行结果取得人工验收，再按原流程归档。未完成的 CI 与人审不计为通过。

## 允许修改的位置

| 位置 | 具体用途 |
| --- | --- |
| 隔离试点 `AGENTS.md`、`README.md`、`.gitignore`、`package.json`、`tsconfig.json`、`settings/v2/packages/`、`build-options.android.json` | 固定工程环境、平台构建、忽略缓存及原流程入口；不修改全局安装 |
| `openspec/config.yaml`、`openspec/changes/consume-approved-cocos-menu/`、`harness/openspec-profile.json`、项目级 OpenSpec 包／入口 | 原 Standard 入口、唯一 Tasks、审阅证据、绑定；沿仓库已锁版本和适配器，不新增调度 |
| `assets/scenes/Menu.scene`、`assets/scripts/MenuState.ts`、`MenuScreen.ts`、`RuntimeObservation.ts` 及各自 `.meta` | Cocos 场景、菜单状态、渲染和只读观察 |
| `assets/resources/ui/menu/` 与 `.meta` | 获批两张 PNG、tokens；保存导入 UUID 和派生关系 |
| `native/engine/android/` 内 `AppActivity.java`、`HarnessObservation.java`、`AndroidManifest.xml`、必要构建参数 | Android Back／生命周期桥、仅调试构建的只读观察与固定原生构建；不改全局引擎 |
| `tests/menu-state.*`、`tests/cocos-menu/`、`scripts/build-cocos-android.py`、`scripts/test-cocos-android.py` | 行为测试、真实触控及原生构建／运行；不使用网页结果冒充设备测试 |
| `harness/ui-design/`、`.agents/skills/ui-design-workflow/`、`scripts/ui-design-check`、`harness/ui-ci/`、`design-inputs/`、`evidence/` | 原工具完整副本、已审输入与实际证据；共同规则及规则锁不改 |
| 教程 `engineering-harness/templates/ui-design/ci/cocos-android.py`、`github-cocos-android.yml.example`，对应定向测试和现行接入说明 | 若试点确需复用，提供薄平台入口；复用 `check_inputs.py`，平台文件不进入另一套共同规则。说明只增补实际已验范围 |

导出生成的 `library/`、`temp/`、`build/` 与 Gradle 缓存留在隔离目录。实际必需的生成源码在首次基线中逐项清点；出现上述位置之外的实质范围变更，先记录原因和影响，再交回决定。

## CI 和公开操作边界

后续拟用单独的公开试点 `liam-i/ui-harness-pilot-cocos-20261009`，避免替换现有 iOS 试点及其必需检查。当前账号只读查询返回 404；尚未创建，不能据此保证名称一定可创建。

该后续审核将列出：实际源码提交与上传清单、一个本人同仓库 PR、临时 macOS ARM64 Runner、复用两台专用 AVD、`cocos-native-ui` required check、公开库全部外部 fork 审批、固定的 Actions 与 SDK 身份、成功及失败产物的留存。只公开试点源、许可允许的设计资源和脱敏证据；不上传教程主仓库、凭据、完整 SDK／引擎、缓存或无关设备信息。结束撤销 Runner，关闭本次设备。

本次工程审核不提前授权这项尚未生成源码的远程操作。设计发布则已有完整[批准恢复包](../open-design-review/approval/design-approved.bundle)及[逐文件清单](inputs.json)，属于本次可审阅的具体操作。

## 本阶段通过条件与停点

- 共同 current 检查绑定实际 A/D、policy、消费者、工作区与授权，结果完整通过。
- 两设备各 C01–C16 全部执行，无缺失、失败、跳过或超时；设计包、资源、Scene、运行 APK 可追溯。
- 七状态截图、best=0 弹窗变体、安全区、字号、方向及实际触控有证据；未取得人审前只能记为自动核查结果。
- 有界失败保留原始记录；实际输入、平台故障及恢复义务仍按已审合同执行。
- 先提交本地实现和运行证据供查看；后续真实 CI 与人工运行验收完成前，不结项 open-design／Cocos，也不结束完整补充目标。

本次审批只需确认本页及四份原 Change 文件，允许发布固定设计并开始上述本地 Apply。当前没有实施代码、没有新建远程试点或 Runner，也没有重复请求已完成的设计批准。
