# tesla_scanner

Scans 5 crypto pairs every 15 minutes across 3 timeframes (4H / 1D / 1W).
Sends Telegram alerts when price approaches or hits key moving-average levels,
manual support/resistance levels, or when MA crossovers occur.

---

## A) Run locally in VS Code

**1. Install dependencies**
```
pip install -r requirements.txt
```

**2. Configure environment**
```
cp .env.example .env
```
Edit `.env`. You can configure either or both notification channels — any
channel with its env var set will receive alerts; ones left blank are skipped.

**Telegram** (optional):
```
TELEGRAM_BOT_TOKEN=<your token>
TELEGRAM_CHAT_ID=<your chat id>
```
Get your **bot token**: message [@BotFather](https://t.me/BotFather), send `/newbot`, follow the
prompts, copy the token. Get your **chat ID**: send any message to your bot,
then open `https://api.telegram.org/bot<TOKEN>/getUpdates` — look for
`"chat":{"id": ...}`.

**Discord** (optional):
```
DISCORD_WEBHOOK_URL=<your webhook url>
```
Get your **webhook URL**: in Discord, open the channel you want alerts in →
**Edit Channel → Integrations → Webhooks → New Webhook** → copy the URL.

**3. Test a single scan (no 15-minute wait)**
```
python scanner.py --once
```
If Telegram is not configured, alerts are printed to the console instead.

**4. Run continuously**
```
python scanner.py
```

---

## B) Deploy to Railway via GitHub

**1.** Push this directory to a GitHub repository.

**2.** On [Railway](https://railway.app): **New Project → Deploy from GitHub repo** → select your repo.

**3.** In the Railway dashboard, go to **Variables** and add whichever
notification channels you want (either or both):
```
TELEGRAM_BOT_TOKEN  = <your token>
TELEGRAM_CHAT_ID    = <your chat id>
DISCORD_WEBHOOK_URL = <your webhook url>
```

**4. Persist the SQLite database across redeploys**
Railway's filesystem is wiped on every redeploy. To preserve scan history and
alert dedup state, attach a Railway Volume:
- In your service, go to **Settings → Volumes → Add Volume**
- Mount path: `/data`
- Add a variable: `DB_PATH=/data/tesla_scanner.db`

**5.** Confirm the worker process starts correctly — Railway reads `Procfile`
automatically:
```
worker: python scanner.py
```
Check **Logs** in the Railway dashboard to see scan output.

---

## Editing pairs and levels

Open `config.py`. Everything a user needs to touch is there:

- `PAIRS` — symbols and per-pair proximity thresholds
- `LEVELS` — manual price levels per pair (flat list, role assigned automatically)
- `MA_CROSS_PAIRS` — which SMA pairs to watch for crossovers
