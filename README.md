# 🤖 Advanced Telegram Bot
## Author: Vikram Singh
A feature-rich Telegram bot with AI chat, weather, news, trivia game, and notes system.  
Built with Python · Deployed on Railway (free, 24/7 uptime)

---

## ✨ Features

| Command | Description |
|---|---|
| `/start` | Welcome message |
| `/help` | Full command list |
| `/time` | Current date & time |
| `/weather <city>` | Live weather with temperature, humidity, wind |
| `/news` | Top 5 world headlines |
| `/joke` | Random programming joke |
| `/note <text>` | Save a personal note |
| `/notes` | View all your saved notes |
| `/clearnotes` | Delete all your notes |
| `/trivia` | Interactive trivia with tap buttons |
| `/ai <question>` | Ask AI anything |
| *(any text)* | AI replies automatically — conversational! |

---

## 🚀 Setup (Local)

### Step 1 — Get your Bot Token
1. Open Telegram → search **@BotFather**
2. Send `/newbot` and follow the steps
3. Copy the token it gives you (looks like `123456789:ABCdef...`)

### Step 2 — Get your Anthropic API Key
1. Go to **https://console.anthropic.com**
2. Sign up (free) → API Keys → Create Key
3. Copy the key

### Step 3 — Install & Run
```bash
# Clone or download this folder
cd telegram_bot

# Install dependencies
pip install -r requirements.txt

# Set environment variables (Linux/Mac)
export BOT_TOKEN="your_telegram_token_here"
export ANTHROPIC_API_KEY="your_anthropic_key_here"

# On Windows CMD:
set BOT_TOKEN=your_telegram_token_here
set ANTHROPIC_API_KEY=your_anthropic_key_here

# Run the bot
python main.py
```

---

## ☁️ Deploy on Railway (24/7 Free Hosting)

Railway gives you **500 free hours/month** — more than enough to run your bot.

### Step 1 — Push code to GitHub
```bash
git init
git add .
git commit -m "Initial bot"
# Create a repo on github.com, then:
git remote add origin https://github.com/YOUR_USERNAME/telegram-bot.git
git push -u origin main
```

### Step 2 — Deploy on Railway
1. Go to **https://railway.app** → Sign up with GitHub
2. Click **New Project** → **Deploy from GitHub repo**
3. Select your repository

### Step 3 — Add Environment Variables
In Railway dashboard → your project → **Variables** tab → Add:
```
BOT_TOKEN        = your_telegram_bot_token
ANTHROPIC_API_KEY = your_anthropic_api_key
```

### Step 4 — Deploy!
Railway will automatically:
- Detect Python
- Install `requirements.txt`
- Run `python main.py`
- Keep it running 24/7 ♾️

---

## 📁 Project Structure

```
telegram_bot/
├── main.py                  # Entry point — registers all handlers
├── requirements.txt         # Python dependencies
├── Procfile                 # Railway process config
├── railway.json             # Railway deployment config
├── notes_db.json            # Auto-created — stores user notes
└── handlers/
    ├── start.py             # /start, /help, /about
    ├── utilities.py         # /time, /weather, /news
    ├── jokes.py             # /joke
    ├── notes.py             # /note, /notes, /clearnotes
    ├── trivia.py            # /trivia (inline buttons)
    └── ai.py                # /ai + plain message AI handler
```

---

## 🛠 Common Errors

| Error | Fix |
|---|---|
| `Unauthorized` | Wrong BOT_TOKEN — check it |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| AI returns 401 | Wrong ANTHROPIC_API_KEY |
| AI returns 429 | Rate limit hit — wait a minute |
| Bot not responding | Check Railway logs for errors |

---

## 💡 Ideas to Add Next
- `/remind 10m Buy milk` — timed reminders
- `/calc 2+2*10` — calculator
- `/translate Hello` — translate to Hindi
- User stats (how many questions asked, notes saved)
- Admin-only commands (broadcast message to all users)
# Babamosie_Bot
