import requests
import time
import os
import re
import json
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def get_price(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")

    price = soup.select_one(".a-price-whole")
    if price:
        price = re.sub(r"[^\d]", "", price.text)
        return int(price)

    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ابعت رابط Amazon.eg وأنا أتابع السعر")

async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if "amazon.eg" not in url:
        await update.message.reply_text("الرابط لازم يكون Amazon.eg")
        return

    data = load_data()
    chat_id = str(update.message.chat_id)

    price = get_price(url)

    if price is None:
        await update.message.reply_text("مش قادر أجيب السعر")
        return

    if chat_id not in data:
        data[chat_id] = []

    data[chat_id].append({
        "url": url,
        "price": price,
        "interval": 600,
        "last_check": 0
    })

    save_data(data)

    await update.message.reply_text(f"تمت الإضافة\nالسعر الحالي: {price} جنيه")

async def check_prices(app):
    while True:
        data = load_data()
        now = time.time()

        for chat_id in data:
            for item in data[chat_id]:
                if now - item["last_check"] > item["interval"]:
                    new_price = get_price(item["url"])

                    if new_price and new_price < item["price"]:
                        await app.bot.send_message(
                            chat_id=int(chat_id),
                            text=f"""📉 السعر انخفض
💰 كان: {item['price']} جنيه
🔥 أصبح: {new_price} جنيه
🔗 {item['url']}"""
                        )
                        item["price"] = new_price

                    item["last_check"] = now

        save_data(data)
        await asyncio.sleep(60)

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_product))

    app.job_queue.run_once(lambda *_: app.create_task(check_prices(app)), 1)

    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
