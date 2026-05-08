#!/usr/bin/env python3
"""
Daily report: fetches open tickets from Jira, open conversations and CSAT from Intercom,
then posts an Adaptive Card to a Microsoft Teams channel via webhook.

Required environment variables:
  JIRA_BASE_URL        e.g. https://company.atlassian.net
  JIRA_EMAIL           Atlassian account email
  JIRA_API_TOKEN       Jira API token (https://id.atlassian.com/manage-profile/security/api-tokens)
  JIRA_PROJECT_KEYS    comma-separated project keys, e.g. "PROJ,BACKEND" (optional, omit for all)
  INTERCOM_ACCESS_TOKEN  Intercom access token
  TEAMS_WEBHOOK_URL    Incoming webhook URL for the Teams channel
"""

import os
import sys
import json
import time
from datetime import datetime, timezone
import urllib.request
import urllib.error
import base64

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def http_get(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTP {e.code} for {url}: {body}", file=sys.stderr)
        raise

def http_post(url: str, payload: dict, headers: dict | None = None) -> int:
    data = json.dumps(payload).encode()
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTP {e.code} posting to {url}: {body}", file=sys.stderr)
        raise

def http_post_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 20) -> dict:
    data = json.dumps(payload).encode()
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTP {e.code} posting to {url}: {body}", file=sys.stderr)
        raise

def require_env(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return val

# ---------------------------------------------------------------------------
# Jira
# ---------------------------------------------------------------------------

def fetch_jira_open_tickets(base_url: str, email: str, token: str, project_keys: list[str]) -> dict:
    credentials = base64.b64encode(f"{email}:{token}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Accept": "application/json",
    }

    jql = (
        "statusCategory != Done"
        " AND status NOT IN (Canceled, Closed, Done, Merged, PRODUCTION, Rejected)"
        " AND created >= -12w"
        " AND issuetype = Bug"
        " AND project IN (AD, ANA, ACM, CORE, ENG, INFRA, SUP, KB, PM, PUB, SYNC)"
        " ORDER BY created DESC"
    )

    # Jira Cloud dropped `total` — paginate with cursor API and count locally
    all_issues = []
    next_page_token = None
    while True:
        params: dict = {"jql": jql, "maxResults": 100, "fields": "priority,assignee"}
        if next_page_token:
            params["nextPageToken"] = next_page_token
        url = f"{base_url.rstrip('/')}/rest/api/3/search/jql?{urllib.parse.urlencode(params)}"
        data = http_get(url, headers)
        all_issues.extend(data.get("issues", []))
        if data.get("isLast", True) or not data.get("nextPageToken"):
            break
        next_page_token = data["nextPageToken"]

    total = len(all_issues)
    priority_counts: dict[str, int] = {}
    unassigned = 0
    for issue in all_issues:
        fields = issue.get("fields", {})
        prio = (fields.get("priority") or {}).get("name", "None")
        priority_counts[prio] = priority_counts.get(prio, 0) + 1
        if not fields.get("assignee"):
            unassigned += 1

    return {
        "total": total,
        "priority_counts": priority_counts,
        "unassigned": unassigned,
        "project_keys": project_keys,
    }

# ---------------------------------------------------------------------------
# Intercom
# ---------------------------------------------------------------------------

def fetch_intercom_open_conversations(token: str) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Intercom-Version": "2.11",
    }

    # Search for open + snoozed — GET state= filter is ignored by Intercom API
    total_open = 0
    for state in ("open", "snoozed"):
        resp = http_post_json("https://api.intercom.io/conversations/search", {
            "query": {"field": "state", "operator": "=", "value": state},
            "pagination": {"per_page": 1},
        }, headers)
        total_open += resp.get("total_count", 0)

    # CSAT: sample of 150 most-recently-closed conversations from last 7 days
    thirty_days_ago = int(time.time()) - (7 * 24 * 3600)
    scores = []
    starting_after = None
    while True:
        pagination: dict = {"per_page": 150}
        if starting_after:
            pagination["starting_after"] = starting_after
        resp = http_post_json("https://api.intercom.io/conversations/search", {
            "query": {
                "operator": "AND",
                "value": [
                    {"field": "state", "operator": "=", "value": "closed"},
                    {"field": "updated_at", "operator": ">", "value": thirty_days_ago},
                ],
            },
            "pagination": pagination,
        }, headers, timeout=60)
        for conv in resp.get("conversations", []):
            val = (conv.get("conversation_rating") or {}).get("rating")
            if val is not None:
                scores.append(int(val))
        # one page is enough for a representative CSAT sample
        break

    csat_avg = round(sum(scores) / len(scores), 2) if scores else None
    csat_count = len(scores)

    return {
        "open_conversations": total_open,
        "csat_avg": csat_avg,
        "csat_count": csat_count,
    }

# ---------------------------------------------------------------------------
# Teams Adaptive Card
# ---------------------------------------------------------------------------

def build_adaptive_card(jira: dict, intercom: dict, report_date: str) -> dict:
    # Jira priority rows
    priority_order = ["Highest", "High", "Medium", "Low", "Lowest", "None"]
    priority_emoji = {
        "Highest": "🔴", "High": "🟠", "Medium": "🟡",
        "Low": "🔵", "Lowest": "⚪", "None": "⚫",
    }

    priority_facts = []
    for prio in priority_order:
        count = jira["priority_counts"].get(prio)
        if count:
            emoji = priority_emoji.get(prio, "•")
            priority_facts.append({"title": f"{emoji} {prio}", "value": str(count)})

    # CSAT display
    if intercom["csat_avg"] is not None:
        stars = "⭐" * round(intercom["csat_avg"])
        csat_text = f"{intercom['csat_avg']:.1f} / 5  {stars}  ({intercom['csat_count']} ratings)"
    else:
        csat_text = "No data"

    project_label = "AD, ANA, ACM, CORE, ENG, INFRA, SUP, KB, PM, PUB, SYNC"

    card_body = [
        {
            "type": "TextBlock",
            "text": f"📊 Daily Report – {report_date}",
            "weight": "Bolder",
            "size": "Large",
            "wrap": True,
        },
        # Jira section
        {
            "type": "TextBlock",
            "text": "🟦 JIRA",
            "weight": "Bolder",
            "size": "Medium",
            "spacing": "Medium",
        },
        {
            "type": "TextBlock",
            "text": f"Projects: {project_label}",
            "isSubtle": True,
            "size": "Small",
            "spacing": "None",
        },
        {
            "type": "FactSet",
            "facts": [
                {"title": "Open tickets total", "value": str(jira["total"])},
                {"title": "Unassigned", "value": str(jira["unassigned"])},
            ] + priority_facts,
        },
        # Intercom section
        {
            "type": "TextBlock",
            "text": "💬 INTERCOM",
            "weight": "Bolder",
            "size": "Medium",
            "spacing": "Medium",
        },
        {
            "type": "TextBlock",
            "text": "Support Overview",
            "isSubtle": True,
            "size": "Small",
            "spacing": "None",
        },
        {
            "type": "FactSet",
            "facts": [
                {"title": "Open Conversations", "value": str(intercom["open_conversations"])},
                {"title": "CSAT Score", "value": csat_text},
                {"title": "", "value": "_(based on last 7 days)_"},
            ],
        },
        {
            "type": "TextBlock",
            "text": f"Generated on {report_date} · automated via GitHub Actions",
            "isSubtle": True,
            "size": "Small",
            "wrap": True,
            "spacing": "Medium",
        },
    ]

    # Power Automate workflow webhook expects the Adaptive Card directly
    return {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.4",
        "body": card_body,
    }

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import urllib.parse  # noqa: PLC0415 – imported here to keep top-level clean

    jira_base = require_env("JIRA_BASE_URL")
    jira_email = require_env("JIRA_EMAIL")
    jira_token = require_env("JIRA_API_TOKEN")
    jira_projects_raw = os.environ.get("JIRA_PROJECT_KEYS", "").strip()
    jira_projects = [k.strip() for k in jira_projects_raw.split(",") if k.strip()]

    intercom_token = require_env("INTERCOM_ACCESS_TOKEN")
    teams_webhook = require_env("TEAMS_WEBHOOK_URL")

    report_date = datetime.now(tz=timezone.utc).strftime("%d.%m.%Y")

    print("Fetching Jira data …")
    jira_data = fetch_jira_open_tickets(jira_base, jira_email, jira_token, jira_projects)
    print(f"  Jira open tickets: {jira_data['total']}")

    print("Fetching Intercom data …")
    intercom_data = fetch_intercom_open_conversations(intercom_token)
    print(f"  Open conversations: {intercom_data['open_conversations']}, CSAT: {intercom_data['csat_avg']}")

    print("Building Adaptive Card …")
    card = build_adaptive_card(jira_data, intercom_data, report_date)

    print("Posting to Teams …")
    status = http_post(teams_webhook, card)
    print(f"  Teams response status: {status}")

    if status not in (200, 202):
        print(f"Unexpected status {status}", file=sys.stderr)
        sys.exit(1)

    print("Done.")

if __name__ == "__main__":
    main()
