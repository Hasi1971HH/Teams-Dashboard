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

## Changing the target channel

The target channel is controlled entirely by the **webhook URL** — there is no channel ID anywhere in the code.

To post to a different Teams channel:

1. In the desired channel in Teams: **···** → **Connectors** → **Incoming Webhook** → create a new webhook and copy the URL
2. In your GitHub repository under **Settings → Secrets and variables → Actions**, update the `TEAMS_WEBHOOK_URL` secret with the new URL

That is the only change needed — neither the workflow file (`.github/workflows/daily-teams-report.yml`) nor the script (`scripts/daily_report.py`) need to be touched.

## Schedule

The workflow is scheduled at **06:00 UTC Monday–Friday**, targeting a delivery time of around **10:00 CEST / 09:00 CET**.

The cron is set 2 hours earlier than the target because GitHub Actions queues scheduled jobs during peak hours, which typically causes delays of 1–3 hours. Setting the cron earlier compensates for this.

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
