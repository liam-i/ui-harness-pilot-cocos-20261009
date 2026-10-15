## Context

本设计只落实已审 Cocos Android 消费者。固定引用及环境观察见工程审核页 `inputs.json`；D=`c0156a9bbe28a80ae39f55a93132c459e3476190`，A=`a5b141b41e194026841602967f3d4efe81dfb431`。技术可行性已证明空场景构建／加载；实际菜单、原生测试与 CI 仍须实测。

## Goals / Non-Goals

目标是通过原 Standard 链路消费完整获批包，验证七状态、两设备及失败恢复。范围沿 D 的 handoff；不扩充玩法、存档、辅助功能或物理设备指标，不调整 Source of Truth 或共同 checker。

## Decisions

### 原流程和固定输入

设计先按真实批准发布，再执行 current `propose`；本审阅副本成为实际 Change 后固定 Proposal、真实工程审阅与 bindings。固定 policy 使用已审权威／角色；闭包 policy 与消费者 policy 之间保留共同模型要求的完整依据链。绑定覆盖 Spec 的菜单、生命周期、呈现资源及验证义务，不以 runtime 日志反推分母。

工程开始／恢复分别 current `start`／`resume`。本地工具和 CI 复用现有 checker；UI PASS 不替代本次 Apply 请求、行为测试或运行人审。业务代码、记录和必要本地提交只在隔离试点；教程仓库仅保存明确的模板／测试／说明差异及证据，不提交主仓库。

### Scene、状态和素材

`Menu.scene` 保存真实 Scene/Canvas/Camera 和启动组件。`MenuState.ts` 保存 best、是否有会话、会话标识及 screen；`MenuScreen.ts` 用真实 Cocos Node、Label、Sprite、Button 和 BlockInputEvents 呈现菜单、弹窗与会话。转移直接落实已审表格，不创建通用状态框架。

从固定 D 导出到新目录，核对清单后将两张原字节 PNG 与 tokens 放入 `assets/resources/ui/menu/`。Creator 导入得到 `.meta`/SpriteFrame UUID，记录原文件→UUID→Scene/组件→构建产物→运行加载关系。资源加载失败显式失败；禁止静默换占位图。系统字体使用本镜像实际字形，字号与内容按 D。

Canvas 使用 FIT_WIDTH 375；布局按实际可用高度及 ≤700 分支应用 36/70、26/38、20/42 间距。SafeArea 以真实 native 窗口 inset 和实际渲染视口核对，不能把全屏像素等同于安全内容高；若两者与 D 无法同时满足，先记录冲突，不缩控件或裁剪。9-slice、禁用和按压参数严格沿 handoff。

### Android 系统交互和只读观察

Java 与脚本使用安装源码中存在的 `JsbBridge`／`native.bridge`，游戏线程通过 `CocosHelper.runOnGameThread` 调度。Back 只派发到同一菜单处理逻辑；原生 Activity 的系统回调与引擎按键必须去重，且在 API 37 上验证真实 Back。根菜单离开前台通过原生 Activity 处理；存活进程 Home/resume 不重建菜单数据。

测试只通过真实 `adb input tap/keyevent` 和正常 Activity 生命周期驱动状态。调试构建的 `RuntimeObservation.ts` 在完成实际绘制帧后读取真实 Node/Label/Sprite 的矩形、可见性、文字、字号、资源 UUID、当前状态和会话标识，经桥写入应用私有观察文件；主机以 `run-as` 只读取得。观察接口不接受设置状态或执行任意 JS 的命令，不成为业务行为入口。截图直接来自设备，观察值只用作独立断言的实际值，不能自行报告测试 PASS。

### 构建和测试

复用已实测 JDK 17.0.20.1+1、Gradle 8.13、AGP 8.10.1、NDK 28.2.13676358、CMake 3.22.1、SDK 36 和 Creator 3.8.8。工程使用 Android arm64-v8a，专用镜像是 API 37、16 KB 页；不全局切换 JDK／SDK／引擎。Creator 退出 36 只表示导出完成，仍须 Gradle 退出 0、实际 APK 可安装、Scene 加载及测试通过。

状态行为先用独立输入／预期测试，再接真实组件和设备。主机测试执行已审 C01–C16，在每个用例前使用明确冷启动或真实操作准备前提。截图覆盖七状态、best=0 弹窗及字号变化；比较文案、组件几何、资源身份并做实际视觉审阅。不能以测试桥存在、日志里写了成功或截图文件存在作为通过依据。

平台 runner 核对完整配置、独立受检 SHA、干净源、实际 APK、设备身份与精确 device/case 集合。超时沿 D：Creator 600 秒、原生构建 900 秒、启动每设备 240 秒、每设备 suite 300 秒、每 case 30 秒、CI Job 60 分钟。失败不无限重试；先定位并保存，再定向运行。清理只关闭本次 AVD／独立 ADB，恢复字号和方向；测试未完成必须保留失败状态。

### 真实 CI

本地通过后才准备公开源码／工作流审核。拟独立 Cocos 仓库，Mac ARM64 临时 Runner 执行共同输入检查→实际构建／两设备运行→再次观察权威；托管聚合 Job 用 `always()` 要求原生 Job 真正 success。必需检查名 `cocos-native-ui`，固定 GitHub Actions 来源；全部外部 fork 先审批、仅本人同仓库 PR，Runner 不装系统服务。

在实际新 Job 保留正常→平台构建失败→恢复，及共同输入缺失→恢复；必要步骤跳过、取消、结果缺失、零用例和身份不符在平台适配器测试中拒绝。真实平台失败与共同输入失败不能只由本地测试替代。真实 CI/产物/required check 完成后再取得人审运行结论。

## Risks / Trade-offs

- 浏览器参考与 Cocos 字体不同：沿已审 SYSTEM-GLYPHS，固定阈值和文字完整性，不能自行放宽。
- API 37 Back、系统提示和 inset 可能与空场景不同：正常处理提示后验真界面，真实按键与截图发现问题后在上述边界修复。
- 模板生成内容可能漂移：固定安装身份与 build options，记录实际源码及资源产物，不接受只有编辑器预览的替代结果。
- 设计权威在检查后前进：每次工程动作和 CI 前后重查；不得复用旧绿色结果或强行回退 main。

## Migration Plan

本框架无历史业务兼容要求；本轮创建隔离消费者，失败保留现场与日志，不迁移现有工程。旧 iOS 试点与原审核历史保留原字节。完成后将源码与产物恢复材料留存，临时现场清理前进行独立恢复。

## Open Questions

当前设计没有待定问题。工程 Apply 与设计发布待本次真实审核；新工程远程上传、Runner 和运行验收按具体结果后续审核。Figma/Unity 条件不阻断本 Cocos 独立分支，但仍阻断整轮最终完成。
