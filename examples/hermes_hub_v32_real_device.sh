#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Hermes HUB × Open-AutoGLM V3.2 真机部署脚本
#
# JM 9/17 实战: A58 + ESP32 同台协作部署完整流程
#
# 前置:
#   - phonebot-r1 已 git clone 在 /home/ubuntu/phonebot-r1
#   - A58 无线调试开启(配对码 + 端口)
#   - ESP32 V3.2 固件已烧到笔记本 COM5
#   - phonebot-r1 APK 11.2M 推到 A58 安装
#
# 使用:
#   export A58_IP=100.110.37.65
#   export A58_ADB_PORT=36271
#   bash examples/hermes_hub_v32_real_device.sh

set -euo pipefail

A58_IP="${A58_IP:-100.110.37.65}"
A58_ADB_PORT="${A58_ADB_PORT:-36271}"
ADB_SERIAL="${A58_IP}:${A58_ADB_PORT}"
PHONEBOT_DIR="${PHONEBOT_DIR:-/home/ubuntu/phonebot-r1}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*"; exit 1; }

echo "============================================================"
echo "  Hermes HUB × Open-AutoGLM V3.2 真机部署"
echo "  A58: $ADB_SERIAL"
echo "  phonebot-r1: $PHONEBOT_DIR"
echo "============================================================"
echo

# Step 1: ADB connection
echo "--- Step 1: ADB 连接 A58 ---"
if ! adb devices | grep -q "$ADB_SERIAL.*device$"; then
    warn "ADB 离线,尝试重连..."
    adb connect "$ADB_SERIAL" 2>&1 | head -1
    sleep 2
fi
adb devices | grep "$ADB_SERIAL" || err "ADB 连接失败"
log "A58 ADB 在线"
echo

# Step 2: ESP32 USB CDC check
echo "--- Step 2: ESP32 USB CDC 检查 ---"
USB_NODES=$(adb -s "$ADB_SERIAL" shell ls /dev/bus/usb/001/ 2>&1)
echo "USB nodes: $USB_NODES"
adb -s "$ADB_SERIAL" shell dumpsys usb 2>&1 | grep -q "vendor_id=12346" || err "ESP32 vendor_id=12346 不在 USB 总线"
log "ESP32 USB CDC 已连接"
echo

# Step 3: PhoneBot APP check
echo "--- Step 3: PhoneBot APP 检查 ---"
APP_PID=$(adb -s "$ADB_SERIAL" shell pidof com.phonebot.r1 2>&1 | tr -d '\r')
if [ -z "$APP_PID" ]; then
    warn "PhoneBot APP 未启动,启动..."
    adb -s "$ADB_SERIAL" shell am start -n com.phonebot.r1/.MainActivity
    sleep 5
    APP_PID=$(adb -s "$ADB_SERIAL" shell pidof com.phonebot.r1 | tr -d '\r')
fi
[ -n "$APP_PID" ] || err "PhoneBot APP 启动失败"
log "PhoneBot APP pid=$APP_PID"
echo

# Step 4: Start USB CDC service
echo "--- Step 4: 启动 USB CDC 服务 ---"
adb -s "$ADB_SERIAL" shell input tap 360 1274  # 测试 USB wave 按钮
sleep 4
adb -s "$ADB_SERIAL" logcat -d 2>&1 | grep -q '<< {"ok":true,"cmd":"emotion","emotion":"wave"' \
    || err "USB CDC wave 测试失败 — 服务没连上 ESP32"
log "USB CDC 链路通了(wave → ok:true)"
echo

# Step 5: Smoke test 9 emotion
echo "--- Step 5: 9 emotion smoke test ---"
PYBIN="${PYBIN:-python3}"
$PYBIN "$OLDPWD/../scripts/hermes_hub_v32_smoke.py" || err "smoke test 有表情失败"
log "9 emotion 全通过"
echo

# Step 6: Streaming voice bridge check
echo "--- Step 6: 流式语音桥检查 ---"
if systemctl --user is-active phonebot-voice-bridge.service 2>&1 | grep -q "active"; then
    log "voice_bridge systemd 跑着"
else
    warn "voice_bridge systemd 没跑,启动..."
    systemctl --user start phonebot-voice-bridge.service
    sleep 3
fi

# Test streaming endpoint
START=$(date +%s.%N)
HTTP_OUT=$(timeout 8 curl -sS -N -X POST http://127.0.0.1:8766/api/chat_stream \
    -H 'Content-Type: application/json' \
    -d '{"text":"你好","user_id":"deploy_test"}' 2>&1 | head -3)
END=$(date +%s.%N)
DURATION=$(echo "$END - $START" | bc)

if echo "$HTTP_OUT" | grep -q '"type":"sentence"'; then
    log "流式端点 OK($DURATION 秒)"
    echo "  响应样例:$(echo "$HTTP_OUT" | head -1 | head -c 120)"
else
    err "流式端点没回包: $HTTP_OUT"
fi
echo

echo "============================================================"
log "V3.2 真机部署完成"
echo "  - A58 APP + ESP32 USB CDC 链路通"
echo "  - 9 emotion 全 ok:true"
echo "  - /api/chat_stream 流式 OK"
echo
echo "下一步:"
echo "  - bash examples/hermes_hub_dual_run.sh  # 同启 Open-AutoGLM + Hermes HUB"
echo "  - python scripts/hermes_hub_v32_smoke.py  # 重复跑 smoke test"
echo "============================================================"