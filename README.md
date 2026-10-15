# Cocos Android 菜单试点

消费已审 UI-OD-COCOS-MENU/U001。唯一 Change 为 consume-approved-cocos-menu；本次同步与归档完成后保存于 `openspec/changes/archive/2026-10-09-consume-approved-cocos-menu/`，主 Spec 为 `openspec/specs/cocos-menu/spec.md`。固定批准、工程授权及运行验收见 evidence/engineering-review。完整玩法、持久化和真机性能不在本试点范围。

本地及真实 GitHub CI 的正常、两次恢复均通过两台专用 Android 模拟器各 C01–C16；编译故障与输入缺失都阻断 PR。用户已确认固定版本运行验收，见 `evidence/engineering-review/runtime-acceptance.json`。原生受检源码为 `141ff07280a1d73ff2339e8cabff70d8e388a809`；后续本地证据／归档提交与该运行版本分别记录。公开 PR #1 尚未合并，归档后的本地提交尚未推送或执行远程 CI。

## 构建与验证

工具范围为 Creator 3.8.8、JDK 17.0.20.1+1、Gradle 8.13、AGP 8.10.1、NDK 28.2.13676358、SDK 36；运行设备为已审 API 37 ARM64／16 KB 镜像。固定路径和专用缓存放在仓库外的主机 JSON；CI 用 `COCO_ANDROID_HOST_CONFIG` 传入，不修改全局设置。项目级行为检查为 `npm run test:state`。

```bash
python3 -B harness/ui-design/ci/cocos-android.py \
  --root "$PWD" --head "$CHECKED_SHA" \
  --config harness/ui-ci/cocos-android.json \
  --host-config "$COCO_ANDROID_HOST_CONFIG" \
  --output "$COCOS_EVIDENCE/native"
```

`CHECKED_SHA` 来自独立宿主的完整提交；`COCOS_EVIDENCE` 是项目外已有目录，`native` 必须尚不存在。先后运行共同 `check_inputs.py`，具体参数见 `.github/workflows/cocos-native-ui.yml`。设备控制使用本次独立 ADB／AVD 端口；取消或失败保留日志并清理，清理未知时人工核对专用进程后再运行，不无限重试。

## 来源与许可

按钮 PNG 是 Kenney CC0 原文件，许可见 `assets/resources/ui/menu/LICENSE-kenney.txt`。Cocos 生成代码及引擎的许可保留在 `evidence/engineering-review/Cocos-LICENSE.md`；Superpowers Lite 的固定来源及许可位于 `third_party/superpowers-lite/codex/`。SDK、引擎安装、缓存、账号与凭据不属于上传源码。
