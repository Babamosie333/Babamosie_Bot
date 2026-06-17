# ============================================================
#  handlers/finance.py
#  /crypto <coin> — Live crypto prices
#  /currency <amount> <from> <to> — Currency converter
#  /stock <symbol> — Stock price lookup
# ============================================================

import requests
from telegram import Update
from telegram.ext import ContextTypes

# ── Crypto ────────────────────────────────────────────────

CRYPTO_IDS = {
    "btc": "bitcoin", "eth": "ethereum", "bnb": "binancecoin",
    "xrp": "ripple", "ada": "cardano", "sol": "solana",
    "doge": "dogecoin", "dot": "polkadot", "matic": "matic-network",
    "ltc": "litecoin", "shib": "shiba-inu", "avax": "avalanche-2",
    "link": "chainlink", "uni": "uniswap", "atom": "cosmos",
    "bitcoin": "bitcoin", "ethereum": "ethereum", "dogecoin": "dogecoin",
    "solana": "solana", "cardano": "cardano",
}


async def crypto_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/crypto <coin> — Get live cryptocurrency price."""
    if not context.args:
        await update.message.reply_text(
            "💰 *Crypto Price Lookup*\n\n"
            "`/crypto BTC` — Bitcoin\n"
            "`/crypto ETH` — Ethereum\n"
            "`/crypto DOGE` — Dogecoin\n"
            "`/crypto SOL` — Solana\n"
            "`/crypto BNB` — Binance Coin",
            parse_mode="Markdown"
        )
        return

    coin_input = context.args[0].lower()
    coin_id    = CRYPTO_IDS.get(coin_input, coin_input)

    await update.message.chat.send_action("typing")

    try:
        url  = f"https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": coin_id,
            "vs_currencies": "usd,inr",
            "include_24hr_change": "true",
            "include_market_cap": "true",
        }
        resp = requests.get(url, params=params, timeout=8)
        data = resp.json()

        if coin_id not in data:
            await update.message.reply_text(
                f"❌ Coin `{coin_input.upper()}` not found.\n"
                "Try: BTC, ETH, DOGE, SOL, BNB, ADA, XRP",
                parse_mode="Markdown"
            )
            return

        info   = data[coin_id]
        usd    = info.get("usd", 0)
        inr    = info.get("inr", 0)
        change = info.get("usd_24h_change", 0)
        mcap   = info.get("usd_market_cap", 0)

        arrow  = "📈" if change >= 0 else "📉"
        sign   = "+" if change >= 0 else ""
        mcap_b = f"{mcap / 1e9:.2f}B" if mcap > 1e9 else f"{mcap / 1e6:.2f}M"

        await update.message.reply_text(
            f"💰 *{coin_input.upper()} / {coin_id.title()}*\n\n"
            f"💵 USD: *${usd:,.4f}*\n"
            f"🇮🇳 INR: *₹{inr:,.2f}*\n"
            f"{arrow} 24h Change: *{sign}{change:.2f}%*\n"
            f"📊 Market Cap: ${mcap_b}\n\n"
            f"_Powered by CoinGecko (free)_",
            parse_mode="Markdown"
        )

    except Exception:
        await update.message.reply_text("❌ Crypto service unavailable. Try again later.")


# ── Currency Converter ────────────────────────────────────

async def currency_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/currency <amount> <FROM> <TO> — Convert currencies."""
    if len(context.args) < 3:
        await update.message.reply_text(
            "💱 *Currency Converter*\n\n"
            "`/currency 100 USD INR`\n"
            "`/currency 500 INR USD`\n"
            "`/currency 50 EUR GBP`\n"
            "`/currency 1 BTC USD`\n\n"
            "Supports 170+ currencies!",
            parse_mode="Markdown"
        )
        return

    try:
        amount   = float(context.args[0])
        from_cur = context.args[1].upper()
        to_cur   = context.args[2].upper()
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Example: `/currency 100 USD INR`", parse_mode="Markdown")
        return

    await update.message.chat.send_action("typing")

    try:
        # ExchangeRate-API free tier (no key needed for basic)
        url  = f"https://open.er-api.com/v6/latest/{from_cur}"
        resp = requests.get(url, timeout=8)
        data = resp.json()

        if data.get("result") != "success":
            await update.message.reply_text(f"❌ Unknown currency: `{from_cur}`", parse_mode="Markdown")
            return

        rates = data.get("rates", {})
        if to_cur not in rates:
            await update.message.reply_text(f"❌ Unknown target currency: `{to_cur}`", parse_mode="Markdown")
            return

        rate   = rates[to_cur]
        result = amount * rate

        await update.message.reply_text(
            f"💱 *Currency Conversion*\n\n"
            f"*{amount:,.2f} {from_cur}* = *{result:,.4f} {to_cur}*\n\n"
            f"📊 Rate: 1 {from_cur} = {rate:.4f} {to_cur}\n"
            f"_Rates updated daily_",
            parse_mode="Markdown"
        )

    except Exception:
        await update.message.reply_text("❌ Currency service unavailable. Try again later.")


# ── Stock Prices ──────────────────────────────────────────

async def stock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stock <symbol> — Get stock price (uses Yahoo Finance unofficial API)."""
    if not context.args:
        await update.message.reply_text(
            "📈 *Stock Price Lookup*\n\n"
            "`/stock AAPL` — Apple\n"
            "`/stock GOOGL` — Google\n"
            "`/stock MSFT` — Microsoft\n"
            "`/stock TSLA` — Tesla\n"
            "`/stock AMZN` — Amazon\n"
            "`/stock RELIANCE.NS` — Reliance (NSE)\n"
            "`/stock TCS.NS` — TCS (NSE)",
            parse_mode="Markdown"
        )
        return

    symbol = context.args[0].upper()
    await update.message.chat.send_action("typing")

    try:
        # Using Yahoo Finance v8 API (free, no key)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()

        result = data.get("chart", {}).get("result")
        if not result:
            await update.message.reply_text(
                f"❌ Stock `{symbol}` not found.\n"
                "For Indian stocks, add `.NS` (e.g. `RELIANCE.NS`)",
                parse_mode="Markdown"
            )
            return

        meta      = result[0]["meta"]
        price     = meta.get("regularMarketPrice", 0)
        prev      = meta.get("chartPreviousClose", price)
        currency  = meta.get("currency", "USD")
        name      = meta.get("longName") or meta.get("shortName") or symbol
        exchange  = meta.get("exchangeName", "")

        change    = price - prev
        change_pct = (change / prev * 100) if prev else 0
        arrow     = "📈" if change >= 0 else "📉"
        sign      = "+" if change >= 0 else ""

        await update.message.reply_text(
            f"📈 *{name}* ({symbol})\n"
            f"🏛 Exchange: {exchange}\n\n"
            f"💵 Price: *{currency} {price:,.2f}*\n"
            f"{arrow} Change: *{sign}{change:.2f} ({sign}{change_pct:.2f}%)*\n"
            f"📊 Prev Close: {prev:,.2f}\n\n"
            f"_Data from Yahoo Finance_",
            parse_mode="Markdown"
        )

    except Exception:
        await update.message.reply_text(
            f"❌ Could not fetch stock data for `{symbol}`.\n"
            "Try adding `.NS` for NSE Indian stocks.",
            parse_mode="Markdown"
        )
