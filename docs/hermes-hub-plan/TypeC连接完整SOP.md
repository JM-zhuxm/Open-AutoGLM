# 🚀 TypeC 连接完整 SOP — JM 开机即用

> **目标**: JM 通知设备开机 → 30 秒内两个终端联通 → 立刻测试昨天功能
> **创建**: 2026-09-15
> **基础**: V3.1.2 APK + CoreS3SE V3.1.2 固件 + voice_bridge 2.0

---

## 📋 一、硬件清单(提前备好)

### 必备
- [ ] **OPPO A58**(插电,USB 调试已开)
- [ ] **TypeC 数据线**(数据+充电,非纯充电线)
- [ ] **win-notebook**(100.74.175.82,已开机,Tailscale 在线)
- [ ] **CoreS3SE**(已烧录 V3.1.2 固件,通过 TypeC 接在笔记本)
- [ ] **Hermes Agent**(本机 cargo20-derp,8766 在跑)

### 文件位置速查
```
APK: /home/ubuntu/phonebot-r1/dist/phonebot-r1.apk
固件: /home/ubuntu/phonebot-r1/dist/firmware/phonebot_cores3se_v3.ino
voice_bridge: 本机 8766(已在跑)
WS URL: wss://183.48.74.9:443/phonebot/ws/voice
```

---

## 📋 二、笔记本到本机 SSH 通路

### JM 需要做的(设备通电后):
```bash
# 笔记本(100.74.175.82)开 SSH 或 Tailscale SSH
# 让本机 cargo20-derp 能远程访问笔记本的串口
```

### 我在 cargo20-derp 等 JM 通知后做的:
```bash
# 1. 验证笔记本可达
ssh 100.74.175.82 echo "OK"

# 2. 看 COM5 在不在
ssh 100.74.175.82 'powershell -c "[System.IO.Ports.SerialPort]::GetPortNames()"'

# 3. 启动 socat 共享 COM5 到 TCP 端口(让本机能直连)
ssh 100.74.175.82 'socat -d -d TCP-LISTEN:7777,reuseaddr,fork /dev/com5,b115200,raw'
```

### 备选方案(笔记本无 socat):
- 用 `com0com` 创建虚拟串口对(笔记本端)+ `ser2net` 共享(本机连)
- 用 ESP32 自带的 WiFi + WebSocket(已支持,跳过 COM5)

---

## 📋 三、A58 → 本机的 ADB 通路

### JM 需要做的:
```bash
# A58 端:
# 1. 设置 → 关于手机 → 连点 7 次"版本号" → 进入开发者模式
# 2. 设置 → 系统 → 开发者选项 → 开启「USB 调试」+「无线调试」
# 3. 记录"无线调试"页面的 IP + 端口(通常 5555 或 45731)
# 4. 通过 TypeC 接 A58 到本机或任何 Tailscale 通的设备
```

### 我在 cargo20-derp 等 JM 通知后做的:
```bash
# 1. 重启 ADB server
adb kill-server && adb start-server

# 2. 连接 A58(用 JM 提供的 IP + 端口)
adb connect <A58_IP>:<A58_PORT>

# 3. 验证连接
adb devices -l
# 期望: 100.110.x.x:xxxx device product:PHJ110 model:PHJ110 device:oppo_mb

# 4. 推送 + 安装 V3.1.2 APK
adb -s <A58_IP>:<A58_PORT> push /home/ubuntu/phonebot-r1/dist/phonebot-r1.apk /data/local/tmp/app.apk
adb -s <A58_IP>:<A58_PORT> shell pm install -r -t /data/local/tmp/app.apk
# -t 用于允许 test apk,避免 -99 静默超时
```

---

## 📋 四、CoreS3SE → voice_bridge 通路

### 情况 A: CoreS3SE 通过 TypeC 接笔记本,笔记本通过 Tailscale 共享
```bash
# 1. 笔记本端 socat 共享 COM5 → TCP 7777(见上)
# 2. ESP32 V3 固件里写明: SERVER_HOST = cargo20.com:443 (走 WSS 反代,跳过笔记本中转)
# 3. ESP32 自己拨号 WSS 直连本机 voice_bridge(已支持)
```

### 情况 B: CoreS3SE 通过 WiFi 直接连本机 voice_bridge
```bash
# 烧录 v3_WIFI 版本(已编译)
固件: /home/ubuntu/phonebot-r1/dist/firmware/public/phonebot_cores3se_v3_WIFI.ino
# 烧录时配置:
#   - WiFi SSID + PWD
#   - WS_HOST = 183.48.74.9 (本机公网 IP)
#   - WS_PORT = 443
#   - WS_PATH = /phonebot/ws/voice
```

### 验证 ESP32 连上:
```bash
# 1. 本机查 device state
curl -s http://127.0.0.1:8766/api/device/state/cores3se | jq '{online, url, fw}'

# 期望: {"online": true, "url": "wss://...", "fw": "v3.1"}

# 2. 触发 wave 动作
curl -X POST http://127.0.0.1:8766/api/emotion/play \
  -d '{"emotion":"wave"}' -H 'Content-Type: application/json'

# 3. 再查 device state
curl -s http://127.0.0.1:8766/api/device/state/cores3se | jq '{emotion, last_action}'
# 期望: {"emotion": "wave", "last_action": "wave"}
```

---

## 📋 五、App 端验证(语音循环 V2.0)

### App 端 V3.1.2 已实现的功能(昨天开发):
1. **语音循环 V2.0**: 「芝麻开门」唤醒 → 8s 对话 → 自动续轮
2. **媒体互锁 V3.1**: 播音乐时锁 VAD,但保留唤醒词通道
3. **STT 预拦截 V3.1.1**: "播放歌曲"直接走媒体,不走 LLM
4. **playEmotion NPE 修复 V3.1.2**: 传 noop callback

### JM 需要做的:
1. 在 A58 桌面点 PhoneBot-R1 图标
2. 进入「语音聊天」界面(VoiceChatActivity)
3. 长按底部"芝麻"按钮进入测试
4. 说"芝麻开门"→ 验证进入长对话
5. 说"播放歌曲"→ 验证媒体播放 + ESP32 表情
6. 说"芝麻关门"→ 验证退出长对话

### App 端日志验证:
```bash
# 实时看 logcat(验证 V3.1.2 在跑)
adb -s <A58_IP>:<A58_PORT> logcat -v time | grep --line-buffered PhoneBot

# 期望看到:
# [PhoneBot] VoiceBridge connected
# [PhoneBot] [V3.1.2] playEmotion noop callback fix
# [PhoneBot] [V3.1-MEDIA] 媒体意图拦截 stt='...' type=music
```

---

## 📋 六、应急 Fallback

### 如果 JM 那边 TypeC 数据线不行:
- 用 ESP32 自带 WiFi(烧录 v3_WIFI 固件)
- 不需要笔记本中转,ESP32 直连 voice_bridge WSS

### 如果 ADB 连接不上:
```bash
# 1. 确认 USB 调试开启
adb -s <IP>:<PORT> shell getprop ro.debuggable
# 期望: 1

# 2. 如果是 adb key 问题
adb -s <IP>:<PORT> shell pm clear com.phonebot.r1   # 清 App 数据重连

# 3. 看 adb server 状态
adb devices -l   # 看 device 是否 online
```

### 如果 ESP32 WS 连不上:
```bash
# 1. 看本机 wss 反代
curl -s http://127.0.0.1:8766/health | jq '.data.components.cores3se_body'
# 期望: {"status": "ok"} 而不是 "offline"

# 2. 看 nginx 日志
tail -20 /var/log/nginx/access.log | grep ws/voice

# 3. 重启 voice_bridge
ps aux | grep voice_bridge | grep -v grep
# 如果挂了,启动新实例
```

---

## 📋 七、30 秒"插上就动"自检清单

JM 设备开机后,**依次执行**:

```
□ 笔记本开 → Tailscale ping 100.74.175.82 通
□ ESP32 插上 → lsusb 看 esp32 设备在
□ voice_bridge 8766 在跑(已在跑)
□ A58 插电 + USB 调试开
□ ADB connect 成功
□ 安装 V3.1.2 APK 成功
□ 启动 App → "芝麻开门" 唤醒成功
□ "播放歌曲" → A58 播音乐 + ESP32 表情变化
□ "芝麻关门" → 退出长对话
```

---

## 📋 八、JM 通知我的标准话术

JM 设备开机后,**一句话告诉我**:

```
"笔记本开 + A58 开 + COM5 在"
```

或者:

```
"A58 没接笔记本,ESP32 用 WiFi"
```

我会立刻执行:
1. SSH 笔记本共享串口
2. ADB 连接 A58 + 装 APK
3. 验证 ESP32 在线
4. 触发 wave/nod 测试
5. 截图 + logcat 发到飞书

---

## 🔗 相关文件

- `01-可行性分析报告.pdf` — TypeC 可行性章节
- `02-主要技术文档.pdf` — USB CDC + JSON 协议
- `06-JM家书.pdf` — 家人说服材料
- `phonebot-r1-app-voice-loop` skill — V2.0/V3.1.2 完整代码注释

---

*本 SOP 由 AI 自动生成,基于昨天 V3.1.2 已实机验证过的功能*