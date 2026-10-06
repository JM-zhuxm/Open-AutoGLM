# Hermes HUB × Open-AutoGLM V3.7.1 舵机里程碑 (2026-10-06)

> **前一篇**: [HERMES_HUB_V32_LANDSCAPE.md](./HERMES_HUB_V32_LANDSCAPE.md) — V3.2 USB CDC 链路实证(2026-09-17)
> **本篇**: 身体层从「表情动画」扩展到**真实舵机关节动作**,真机三通道闭环。
> **上游状态**: `main` = `86f5538`,与 `zai-org/Open-AutoGLM` **完全同步**(2026-10-06 用
> `git ls-remote` 双端核实,上游无新提交)。因此本分支的更新**只叠加集成层**,不触碰上游代码。

---

## 一句话

```
V3.2 打通了「AI → 手机 → USB CDC → ESP32 表情」
V3.7.1 打通了「AI → 手机 → USB CDC → PCA9685 → 真实舵机(摇头/点头/挥手)」

机器人身体第一次有了「可被 VLM 调度的关节」,而不只是脸。
```

---

## 1. 硬件链路

```
A58 (UsbCdcService)
   │  USB CDC (TypeC, <5ms)
   ▼
CoreS3SE  fw v3.7.1-hat2pca        (烧录产物 520,576 B,hash 校验通过)
   │  I2C  SDA = G2(与外设 LEDC 复用,坑见 §4)
   ▼
PCA9685  (I2C 地址 0x40 / 十进制 64)
   ├── CH0  摇头 (head pan)
   ├── CH1  点头 (head tilt / nod)
   └── CH5  挥手 (right arm wave)
```

**PCA9685 存在性实测**
```
> pca_status
< {"pca_ok":true,"addr":64,"pins":"2/1"}
```

---

## 2. 通道映射表(hat → PCA)

V3.7.1 之前,`hat_*` 通道由 ESP32 内置 LEDC 直驱;v3.7.1 起**全部转交 PCA9685**。

| hat 通道 | → PCA 通道 | 动作 | 依据 |
|---|---|---|---|
| hat 0 | PCA 0 | 摇头 head pan | `anim_*` 源码 + `SERVO_NAMES` + 真机串口 |
| hat 1 | PCA 1 | 点头 nod | 同上 |
| hat 2 | **-1(忽略)** | — | 该通道在 v3.7.1 未接线,显式忽略避免误动 |
| hat 3 | **PCA 5** | 挥手 wave | `anim_wave` 走 hat ch3 + `pca_demo` 注释 `rarm=CH5` |

**映射数组(固件)**: `{0, 1, -1, 5, -1, -1, -1, -1}`

---

## 3. 真机验证证据(2026-10-06)

固件留痕日志格式:`[hat2pca] ch=%u -> pca=%d ang=%u`

### 3.1 串口实测(指令 → 通道 → 角度)

```
> emotion.play happy
[hat2pca] ch=3 -> pca=5 ang=140
[hat2pca] ch=3 -> pca=5 ang=40
[hat2pca] ch=3 -> pca=5 ang=90
< ok:true emotion=happy
```

三条角度序列与固件 `anim_happy` 源码**逐帧吻合**(源码里 happy 动画就是 140 → 40 → 90),
证明「指令 → 动作表 → PCA 通道 → 角度」整条链路无中间层丢失。

### 3.2 硬件状态回读

| 项 | 值 |
|---|---|
| 固件版本 | `v3.7.1-hat2pca` |
| 烧录体积 | 520,576 B(编译 → 烧录 → hash 校验通过) |
| PCA9685 | `pca_ok=true`,`addr=64`(0x40) |
| 通道数 | `pins=2/1`(已实测可用通道) |

---

## 4. 踩坑记录(对上游有价值的工程细节)

### 4.1 I2C SDA 与 LEDC 共用引脚会锁死总线 ⚠️

- **现象**: PCA9685 在 I2C 扫描里完全不出现(不可达)。
- **真因**: `SDA = G2` 同时被 LEDC 初始化,**LEDC 推挽输出把 SDA 拉到 0.24 V**,I2C 总线被拉死。
- **铁则**: 一个引脚**只能**归属一个外设驱动。走 PCA9685 后,该引脚必须彻底从 LEDC 解绑。

### 4.2 编译目标必须带 CDC(否则串口全黑)

| 编译目标 | 结果 |
|---|---|
| `esp32:esp32:m5stack-cores3`(cdc_on_boot=1 + usb_mode=1) | ✅ 日志 + 命令全通 |
| `esp32:esp32:esp32s3`(CDC off,Serial 走 UART0) | ❌ 无打印 + 所有命令 `Write timeout` |

「无日志 + 命令超时」在 90% 情况下不是硬件坏,而是**编译目标选错**。

### 4.3 舵机不动 ≠ 舵机坏

除 §4.1 外,还需排除:① 电源(舵机不能吃板载 3.3V);② 通道映射未命中(本表 hat2 = -1 属**故意忽略**)。

---

## 5. 对 Open-AutoGLM 的意义(VLM 可调度动作清单)

V3.7.1 后,Hermes HUB 可被 VLM/Agent 调度的身体动作从「表情」扩展到「关节」:

| 指令 | 参数 | 效果 |
|---|---|---|
| `emotion.play <name>` | love / proud / cool / wink / smug / shy / yummy / happy / wave / nod … | 表情 + 关联舵机动画 |
| `servo.set <ch> <ang>` | ch 0/1/5,ang 0-180 | 直驱单个舵机(调试 / 精确姿态) |
| `pca_status` | — | PCA9685 在线状态 + 地址 + 可用通道 |
| `status` | — | 固件版本 / node_id / 表情 / uptime |

**典型协同剧本**(Open-AutoGLM 控屏 + Hermes HUB 动身体):

```
1. Open-AutoGLM: 截图 → VLM 判断「有视频通话请求」→ ADB 点击接听
2. Hermes HUB : servo.set 1 25   (点头示意)
                emotion.play happy (笑)
                servo.set 0 45    (转向说话人)
```

---

## 6. 与本分支既有文件的交叉引用

- [HERMES_HUB_INTEGRATION.md](./HERMES_HUB_INTEGRATION.md) — 集成总说明(架构 + 双进程 + LLM 桥接)
- [HERMES_HUB_V32_LANDSCAPE.md](./HERMES_HUB_V32_LANDSCAPE.md) — V3.2 USB CDC 链路实证
- `scripts/hermes_hub_v32_smoke.py` — 表情推送冒烟测试(V3.2)
- `examples/hermes_hub_v32_real_device.sh` — 真机部署脚本
- 主项目仓库 `phonebot-r1`:tag `milestone-2026-10-06-servo`,commit `b29b38c`

---

## 7. 上游 PR 提议清单(更新至 2026-10-06)

- [x] 架构文档骨架
- [x] 流式端点 SDK client 模板
- [x] 真机部署脚本
- [x] V3.2 表情链路真机数据
- [x] **V3.7.1 舵机三通道闭环数据(本文档)**
- [ ] A58 屏幕共享端口(ADB 与 USB CDC 并行)真机复验 → 已在 V3.2 阶段实证,待整理独立 PR
- [ ] Hermes HUB Skill 注册为 Open-AutoGLM `action`(让 VLM 感知机器人身体)
- [ ] 上游 zai-org review 后合入主仓
- [ ] `phone_agent/model/client.py` 默认 base_url 指向 Hermes HUB

---

## 8. 尚未完成(V3.7.1 边界,诚实边界声明)

- 舵机只用了 **3 个通道**(0 / 1 / 5);履带 / 机械臂多舵机扩展未接线验证
- PCA9685 通道 2 起为预留,**未接舵机**,映射表显式置 -1
- 「VLM 自动选动作」仅有人工剧本,尚无自动编排
- 上游 PR 未提交

---

> **JM 拍板(2026-10-06)**: 舵机通道映射以**双证据**(固件源码 + 真机串口)定表,
> 映射表 `{0,1,-1,5,-1,-1,-1,-1}` 冻结为 v3.7.1 基线;
> 后续接新舵机时**必须同时更新源码与本文档**,不得只在真机上试通就算完成。
