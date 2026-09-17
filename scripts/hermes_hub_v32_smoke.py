#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hermes HUB × Open-AutoGLM V3.2 smoke test.

通过 ADB 推 emotion.play 命令到 A58 UsbCdcService,
UsbCdcService 通过 USB CDC bulk endpoint 到 ESP32 CoreS3SE V3.2,
ESP32 返回 ok:true 表示链路通。

JM 9/17 实战: 9 emotion 全 ok:true,JM 真看到 cool 表情。

Usage:
    # 1. 配对 + 调试端口
    export A58_IP=100.110.37.65
    export A58_ADB_PORT=36271
    python scripts/hermes_hub_v32_smoke.py

    # 2. 单独测一个表情
    python scripts/hermes_hub_v32_smoke.py --only love

    # 3. 跳过 ADB,直接用 ACTION_TEST_CMD broadcast
    python scripts/hermes_hub_v32_smoke.py --method broadcast
"""

import argparse
import os
import subprocess
import sys
import time

ADB_SERIAL = f"{os.environ.get('A58_IP', '100.110.37.65')}:{os.environ.get('A58_ADB_PORT', '36271')}"

# 7 张 V3.2 新脸 + 2 张老脸,共 9
EMOTIONS = [
    "love",     # ❤️ 头轻歪 + 双手合拢
    "proud",    # 💪 抬头挺胸 + 双手外展
    "cool",     # 😎 单手抬起 + 头轻点
    "wink",     # 😉 头轻歪
    "smug",     # 😏 头后仰
    "shy",      # 😊 低头 + 双手内收
    "yummy",    # 😋 头轻点 3 下
    "happy",    # 😁 笑 + 动臂(老)
    "wave",     # 👋 挥手(老)
]


def adb(cmd, timeout=10):
    """Run adb shell command. Returns (stdout, exit_code)."""
    full = ["adb", "-s", ADB_SERIAL] + cmd.split() if cmd.startswith("shell ") else ["adb", "-s", ADB_SERIAL] + cmd
    try:
        out = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
        return out.stdout.strip(), out.returncode
    except subprocess.TimeoutExpired:
        return "", False


def adb_shell(cmd, timeout=10):
    return adb(f"shell {cmd}", timeout=timeout)


def check_connection():
    """Verify A58 is reachable + ESP32 USB CDC up."""
    print("=== 1. ADB + ESP32 USB CDC 检查 ===")

    out, rc = adb("devices")
    if ADB_SERIAL not in out or "device" not in out:
        print(f"❌ A58 ADB not online: {out}")
        return False
    print(f"✅ A58 ADB online: {ADB_SERIAL}")

    out, rc = adb_shell("ls /dev/bus/usb/001/")
    print(f"USB nodes: {out}")

    out, rc = adb_shell("dumpsys usb")
    if "vendor_id=12346" not in out:
        print("❌ ESP32 vendor_id=12346 not found")
        return False
    print("✅ ESP32 USB CDC present")

    out, rc = adb_shell("pidof com.phonebot.r1")
    if not out:
        print("❌ PhoneBot APP not running")
        return False
    print(f"✅ PhoneBot APP pid: {out}")

    return True


def play_emotion(emotion, method="broadcast"):
    """Send emotion.play via chosen method. Returns True if ESP32 returned ok:true."""
    if method == "broadcast":
        # ACTION_TEST_CMD broadcast (V3.1.9 added)
        cmd_json = '{"cmd":"emotion.play","emotion":"' + emotion + '"}'
        adb_shell(f'am broadcast -a com.phonebot.r1.TEST_CMD -p com.phonebot.r1 --es cmd "{cmd_json}"')
    elif method == "tap_wave_button":
        # Tap the "测试 USB wave" button — fall back to wave emotion
        adb_shell("input tap 360 1444")
    else:
        print(f"❌ unknown method: {method}")
        return False

    # Give ESP32 1s to respond
    time.sleep(1.5)

    # Grep logcat for the reply
    out, rc = adb("logcat -d 2>&1 | grep PhoneBot-Usb | tail -3")
    return f'"ok":true,"cmd":"emotion","emotion":"{emotion}"' in out


def smoke_test(only=None, method="broadcast"):
    if not check_connection():
        print("\n❌ Smoke test FAILED: A58/ESP32 not ready")
        return False

    targets = [only] if only else EMOTIONS

    print(f"\n=== 2. 测 {len(targets)} 个 emotion ({method} 方法) ===")
    passed, failed = [], []

    for emo in targets:
        ok = play_emotion(emo, method=method)
        marker = "✅" if ok else "❌"
        print(f"  {marker} {emo}")
        (passed if ok else failed).append(emo)

    print(f"\n=== 3. 结果 ===")
    print(f"  ✅ 通过: {len(passed)}/{len(targets)} → {passed}")
    if failed:
        print(f"  ❌ 失败: {failed}")

    # Verify ESP32 current emotion
    print(f"\n=== 4. ESP32 status 验真 ===")
    adb_shell('am broadcast -a com.phonebot.r1.TEST_CMD -p com.phonebot.r1 --es cmd "{\\"cmd\\":\\"status\\"}"')
    time.sleep(1)
    out, rc = adb("logcat -d 2>&1 | grep -E 'fw.*v3.2.*emotion' | tail -1")
    if "v3.2" in out:
        print(f"  ✅ ESP32 跑 V3.2:{out[:200]}")
    else:
        print(f"  ⚠️ 验真失败: {out[:200]}")

    return len(failed) == 0


def main():
    parser = argparse.ArgumentParser(description="Hermes HUB V3.2 smoke test")
    parser.add_argument("--only", help="test single emotion (love/proud/cool/...)")
    parser.add_argument("--method", choices=["broadcast", "tap_wave_button"], default="broadcast")
    args = parser.parse_args()

    ok = smoke_test(only=args.only, method=args.method)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()