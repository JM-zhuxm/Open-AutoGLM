# Hermes HUB × Open-AutoGLM 集成说明

> **Fork 来源**: [zai-org/Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM) (Apache-2.0)
> **Fork 地址**: <https://github.com/JM-zhuxm/Open-AutoGLM>
> **本分支**: `hermes-hub-integration`(在 main 之上叠加集成层)
> **目标**: 把 Hermes HUB 的"机器人身体"接入 Open-AutoGLM 的"手机 AI 操作"能力

---

## 一句话定位

Open-AutoGLM = **手机 UI 操作 AI**(屏幕视觉 + ADB 控 Android)
Hermes HUB = **机器人身体控制器**(CoreS3SE 表情 + 舵机 + 履带,USB CDC)
本集成 = **同一台 A58 同时被两套系统协同使用**(多模态 AI 操作手机 + AI 控制机器人)

---

## 集成架构

```
┌──────────────────── A58 (OPPO) ─────────────────────┐
│                                                     │
│   Open-AutoGLM          Hermes HUB                  │
│   (屏幕视觉+ADB UI)     (USB CDC→CoreS3SE)         │
│        │                       │                    │
│   adb control           UsbCdcService               │
│        │                       │                    │
│   screen→VLM→action     emotion.play wave/nod       │
│   e.g.打开微信发消息     servo.set head_pan 45°      │
│                                                     │
│        └───────── 共享 Hermes LLM 链 ───────────┘  │
│              Ark-Plan → MiniMax-M3 → deepseek         │
└─────────────────────────────────────────────────────┘
```

**不冲突的关键**:
- Open-AutoGLM 用 ADB 控制 A58 屏幕 UI(tap/swipe/screenshot)
- Hermes HUB 用 USB CDC 控制 CoreS3SE 表情和身体
- 两者通道完全独立,可同时运行

---

## 本分支交付的文件

| 路径 | 内容 |
|---|---|
| `docs/HERMES_HUB_INTEGRATION.md` | 本文档 |
| `scripts/hermes_hub_adb_bridge.py` | 给 A58 桥接 Hermes LLM 通道的命令模板 |
| `examples/hermes_hub_dual_run.sh` | 一键同启 Open-AutoGLM + Hermes HUB 的脚本 |

---

## 快速上手

### 0. 前提
- A58 无线调试端口开放(本仓库默认假设 `100.110.37.65:35229`)
- CoreS3SE 通过 TypeC 接 A58,USB CDC 已授权(参见主项目文档)

### 1. 单独跑(各自独立)

```bash
# 跑 Open-AutoGLM(操作 A58 屏幕 UI)
python main.py --device-ip 100.110.37.65 --device-port 35229

# 跑 Hermes HUB(独立进程,控制机器人)
# 见主仓库 phonebot-r1/ 的 voice_bridge
```

### 2. 同台协作(推荐)

```bash
# 同时启动两套
bash examples/hermes_hub_dual_run.sh

# Open-AutoGLM 处理"打开某 App 找东西"
# Hermes HUB 处理"找到后用机器人声音回应 + 转头看人"
```

### 3. 共享 LLM

`phone_agent/model/client.py` 是 HTTP 客户端,可改 base_url 指向
Hermes voice_bridge 的 `/api/llm/chat`,复用同一套 Ark-Plan → fallback 链。
详见 `scripts/hermes_hub_adb_bridge.py` 中的 `make_llm_client()` 示例。

---

## 路线图

- [x] 文档骨架
- [x] 双进程同启脚本
- [x] LLM 桥接示例
- [ ] A58 屏幕共享端口(ADB 与 USB CDC 同时跑的真机验证)
- [ ] Hermes HUB Skill 注册为 Open-AutoGLM "action"(让 VLM 知道有机器人身体可用)
- [ ] PR 提议:`hermes-hub-integration` 系列 commits 上游 → 主仓

---

## 上游约定

- 我们在 **`hermes-hub-integration` 分支**迭代,不改 `main`(保持与上游 zai-org 同步干净)
- 上游 rebase 命令:`git rebase jm/main` 后如有冲突优先保留 Open-AutoGLM 框架代码
- LICENSE: 沿用上游 **Apache-2.0**,集成层新文件标注 `// SPDX-License-Identifier: Apache-2.0`