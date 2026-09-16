#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Hermes HUB x Open-AutoGLM: A58 ADB bridge + Hermes LLM client example.
#
# This is a TEMPLATE, not production code.
# Copy it into your project, then edit DEVICE_IP / HERMES_VOICE_BRIDGE_URL / system prompt.

import os
import sys
import json
import urllib.request
import urllib.error

# ---- Configuration ----

DEVICE_IP = os.environ.get("A58_IP", "100.110.37.65")
DEVICE_PORT = int(os.environ.get("A58_ADB_PORT", "35229"))
ADB_SERIAL = f"{DEVICE_IP}:{DEVICE_PORT}"

# Hermes voice_bridge public entry (nginx reverse-proxied to :443/phonebot)
# See phonebot-r1/docs/ for the full deployment story.
HERMES_VOICE_BRIDGE_URL = os.environ.get(
    "HERMES_VOICE_BRIDGE_URL",
    "https://139.199.194.20/phonebot/api/llm/chat",
)

# System prompt: tell the VLM that besides UI control it can also drive the robot body.
HERMES_HUB_SYSTEM_PROMPT = """You are Hermes HUB, a phone AI assistant running on an OPPO A58.
You have two execution channels:
1. Screen UI: use ADB tap/swipe/input to operate Apps on A58 directly.
2. Robot body: emit `hermes.action` to control CoreS3SE face, SG90 gimbal, tracked motion.

If body control is needed, return JSON: {\"hermes_action\": {\"command\": \"...\", \"params\": {...}}}.
Available actions:
- emotion.play: emotion=wave|happy|nod|sad|angry|surprised|thinking|sleepy|dance|bow
- servo.set: head_pan=90 head_tilt=90
- Track: forward / backward / turn_left / turn_right / stop

Do NOT install ChatGPT/Claude (requires root). Do NOT swipe on the lock screen."""


def make_llm_client():
    """Build an LLM client compatible with phone_agent/model/client.py.

    phone_agent expects: client.chat(messages) -> {"content": "..."}.
    We forward to Hermes voice_bridge, which falls back through:
    Ark-Plan -> MiniMax-M3 -> deepseek.
    """
    class HermesLLMClient:
        def __init__(self, url=HERMES_VOICE_BRIDGE_URL):
            self.url = url

        def chat(self, messages):
            payload = {
                "messages": messages,
                "system": HERMES_HUB_SYSTEM_PROMPT,
                "user_id": "open_autoglm_bridge",
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.url, data=data,
                headers={"Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    return json.loads(r.read().decode("utf-8"))
            except urllib.error.URLError as e:
                return {"content": f"[bridge error: {e}]"}

    return HermesLLMClient()


def parse_hermes_action(text: str):
    """Extract hermes.action JSON block from the LLM text reply."""
    if "hermes_action" not in text:
        return None
    start = text.find("{")
    end = text.rfind("}") + 1
    if start < 0 or end <= start:
        return None
    try:
        obj = json.loads(text[start:end])
        return obj.get("hermes_action")
    except json.JSONDecodeError:
        return None


if __name__ == "__main__":
    client = make_llm_client()
    out = client.chat([{"role": "user", "content": "ping"}])
    print(json.dumps(out, ensure_ascii=False, indent=2)[:500])
    if isinstance(out, dict):
        act = parse_hermes_action(out.get("content", ""))
        if act:
            print("\n-> extracted hermes.action:")
            print(json.dumps(act, ensure_ascii=False, indent=2))