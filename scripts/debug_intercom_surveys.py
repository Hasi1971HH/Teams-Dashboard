#!/usr/bin/env python3
"""
Debug script: inspect Intercom Surveys API.
Prints all available surveys and a sample of their responses.

Usage:
  INTERCOM_ACCESS_TOKEN=... python scripts/debug_intercom_surveys.py
"""

import os
import sys
import json
import urllib.request
import urllib.error

TOKEN = os.environ.get("INTERCOM_ACCESS_TOKEN", "").strip()
if not TOKEN:
    print("Missing INTERCOM_ACCESS_TOKEN", file=sys.stderr)
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json",
    "Intercom-Version": "2.11",
}

def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTP {e.code} for {url}:\n{body}", file=sys.stderr)
        return None

# ── 1. List surveys ────────────────────────────────────────────────────────
print("=== GET /surveys ===")
surveys_resp = get("https://api.intercom.io/surveys")
print(json.dumps(surveys_resp, indent=2))

if not surveys_resp:
    sys.exit(0)

surveys = surveys_resp.get("data", [])
print(f"\n→ {len(surveys)} survey(s) found\n")

# ── 2. For each survey: show details ───────────────────────────────────────
for s in surveys:
    sid = s.get("id")
    name = s.get("title") or s.get("name") or "(no title)"
    print(f"--- Survey: {name!r}  id={sid} ---")
    print(json.dumps(s, indent=2))
    print()
