# Teams Dashboard – Daily Report

Automatically fetches data from **Jira** and **Intercom** every weekday morning and posts an **Adaptive Card** to a Microsoft Teams channel via GitHub Actions.

## What gets reported

| Source | Data |
|--------|------|
| Jira | Total open tickets, breakdown by priority, unassigned count |
| Intercom | Open conversations, CSAT score (last 7 days), NPS score (last 30 days) |

## Setup

### 1. Teams – Incoming Webhook

1. In Teams, open the channel → **···** → **Connectors** → **Incoming Webhook**
2. Create a webhook and copy the URL
3. Add it as a GitHub secret: `TEAMS_WEBHOOK_URL`

### 2. Jira – API Token

1. Go to <https://id.atlassian.com/manage-profile/security/api-tokens>
2. Create a token and copy it
3. Add the following GitHub secrets:

| Secret | Value |
|--------|-------|
| `JIRA_BASE_URL` | `https://yourcompany.atlassian.net` |
| `JIRA_EMAIL` | Your Atlassian account email |
| `JIRA_API_TOKEN` | The API token from step 2 |
| `JIRA_PROJECT_KEYS` | Comma-separated project keys, e.g. `PROJ,BACKEND` (leave empty for all projects) |

### 3. Intercom – Access Token

1. Go to **Settings → Developers → Your app → Authentication**
2. Copy the Access Token
3. Add GitHub secret: `INTERCOM_ACCESS_TOKEN`

> **Note on NPS:** The NPS score is fetched via Intercom's Data Export API, which runs an asynchronous export job (takes ~1–3 minutes). The token needs the `Read exports` permission. If no NPS surveys were completed in the last 30 days, "No data" is shown.

### 4. Adding secrets to GitHub

Go to your repository → **Settings → Secrets and variables → Actions → New repository secret**.

## Channel wechseln

Der Ziel-Channel wird ausschließlich über die **Webhook-URL** gesteuert – es gibt keine Channel-ID im Code.

Um in einen anderen Teams-Channel zu posten:

1. Im gewünschten Channel in Teams: **···** → **Connectors** → **Incoming Webhook** → neue Webhook-URL erstellen und kopieren
2. Im GitHub-Repository unter **Settings → Secrets and variables → Actions** den Secret `TEAMS_WEBHOOK_URL` aktualisieren – einfach den alten Wert mit der neuen URL überschreiben

Das ist die einzige Stelle, die geändert werden muss. Weder der Workflow (`.github/workflows/daily-teams-report.yml`) noch das Script (`scripts/daily_report.py`) müssen angefasst werden.

## Schedule

The workflow runs **Monday–Friday at 08:00 UTC** (09:00 CET / 10:00 CEST).

To change the time, edit the `cron` expression in `.github/workflows/daily-teams-report.yml`.

You can also trigger the workflow manually via **Actions → Daily Teams Report → Run workflow**.

## Local testing

```bash
export JIRA_BASE_URL="https://yourcompany.atlassian.net"
export JIRA_EMAIL="you@example.com"
export JIRA_API_TOKEN="your-token"
export JIRA_PROJECT_KEYS="PROJ"
export INTERCOM_ACCESS_TOKEN="your-intercom-token"
export TEAMS_WEBHOOK_URL="https://outlook.office.com/webhook/..."

python scripts/daily_report.py
```
