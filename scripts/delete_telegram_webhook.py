#!/usr/bin/env python3
"""Снять webhook (нужно для режима long polling на ONREZA)."""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

token = (os.getenv("BOT_TOKEN") or "").strip()
if not token:
    print("BOT_TOKEN не задан", file=sys.stderr)
    raise SystemExit(1)

payload = json.dumps({"drop_pending_updates": False}).encode()
req = urllib.request.Request(
    f"https://api.telegram.org/bot{token}/deleteWebhook",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=30) as resp:
    print(resp.read().decode())
