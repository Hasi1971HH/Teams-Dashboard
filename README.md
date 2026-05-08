# Teams Dashboard – Daily Report

Automatically fetches data from **Jira** and **Intercom** every weekday morning and posts an **Adaptive Card** to a Microsoft Teams channel via GitHub Actions.

## What gets reported

| Source | Data |
|--------|------|
| Jira | Total open tickets, breakdown by priority, unassigned count |
| Intercom | Open conversations, CSAT score (last 50 closed conversations) |

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

### 4. Adding secrets to GitHub

Go to your repository → **Settings → Secrets and variables → Actions → New repository secret**.

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
