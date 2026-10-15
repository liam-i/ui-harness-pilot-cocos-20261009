# Change：consume-approved-cocos-menu

## Why

open-design 已产出并获人审批准的菜单包，需要由实际 Cocos Android 工程消费，才能验证设计交接、原生呈现和平台门禁。当前只有工具链空场景及浏览器设计参考，没有菜单原生验收。

## What Changes

- 在 Creator 3.8.8 的隔离最小工程实现固定 D/A 的七状态菜单、重置弹窗与静态会话预览。
- 接入固定文件、原共同 current 检查、Android 构建、两台专用模拟器的 C01–C16 和实际 CI。
- 保留设计产物、素材许可、资源 UUID、独立预期、真实批准、源／产物摘要、失败及恢复。

## Capabilities

### New Capabilities

- `cocos-menu`：获批菜单流程、模拟器适配、设计资源消费及原生验证。

### Modified Capabilities

无。现有 iOS 试点、原需求层、共同 UI 合同和历史批准保持各自范围。

## Impact

修改范围限工程审核页所列隔离 Cocos 工程、必要平台适配及对应证据／接入说明。设计 D、批准 A、独立预期不改；无完整 2048 玩法、持久化、后端、产品发布或真机性能承诺。其他四个补充分支仍须完成。

Source of Truth：业务可观察行为在本 Change Spec，唯一实施任务在 `tasks.md`；视觉／交互设计在获批 D，批准在 A；技术落点在 `design.md`。使用这些原 Artifact，不另建业务任务表。
