import os
import time
import requests
import re
import random
from datetime import datetime
from collections import defaultdict

# ====================== НАСТРОЙКИ ======================
API_KEY = os.getenv("TWITTER_API_KEY")           # ключ с TwitterAPI.io
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")     # токен твоего бота
CHAT_ID = int(os.getenv("CHAT_ID", "0"))          # твой ID

# Группы аккаунтов с интервалами (в секундах)
GROUPS = {
    "frequent": {
        "accounts": ["heyibinance", "binancezh", "binance_boxses"],
        "interval": 1800  # ← ИЗМЕНЕНО: 30 минут = 1800 секунд
    },
    "medium": {
        "accounts": ["Bybit_Official", "Bybit_ZH", "binance"],
        "interval": 17280  # 5 раз в сутки (4.8 часа)
    },
    "rare": {
        "accounts": ["benbybit", "BybitAnnouncements", "BybitSouthAsia", "BybitPlus"],
        "interval": 86400  # 1 раз в сутки
    }
}

# Общий список аккаунтов
TARGET_ACCOUNTS = []
for group in GROUPS.values():
    TARGET_ACCOUNTS.extend(group["accounts"])

# Ключевые слова
KEYWORDS = [
    "box", "бокс", "crypto box", "mystery box", "福袋", "red packet",
    "红包", "口令", "загадка", "riddle", "code", "код", "redeem",
    "big gift", "special", "giveaway"
]
# ======================================================

last_tweet_ids = defaultdict(int)
last_check_time = defaultdict(float)

def get_interval_for_user(username):
    """Возвращает интервал проверки для пользователя"""
    for group in GROUPS.values():
        if username in group["accounts"]:
            return group["interval"]
    return 1800  # запасной вариант (30 мин)

# Разбрасываем время первого запуска
current_time = time.time()
for username in TARGET_ACCOUNTS:
    interval = get_interval_for_user(username)
    last_check_time[username] = current_time - random.uniform(0, interval)

def get_latest_tweets(username):
    """Запрос к TwitterAPI.io"""
    url = "https://api.twitterapi.io/twitter/user/latest_tweets"
    headers = {"x-api-key": API_KEY}
    params = {"userName": username, "count": 5}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("tweets", [])
        else:
            print(f"⚠️ Ошибка API для @{username}: {resp.status_code}")
            return []
    except Exception as e:
        print(f"⚠️ Ошибка запроса для @{username}: {e}")
        return []

def send_to_telegram(text):
    """Отправка в Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"⚠️ Ошибка отправки в Telegram: {e}")

def main():
    print(f"[{datetime.now()}] 🔥 Бот запущен на Railway")
    print(f"📊 Мониторинг {len(TARGET_ACCOUNTS)} аккаунтов:")
    for acc in TARGET_ACCOUNTS:
        print(f"   - @{acc} (интервал: {get_interval_for_user(acc)} сек)")

    while True:
        now = time.time()
        for username in TARGET_ACCOUNTS:
            interval = get_interval_for_user(username)
            if now - last_check_time[username] < interval:
                continue

            last_check_time[username] = now

            try:
                tweets = get_latest_tweets(username)
                if not tweets:
                    time.sleep(2)
                    continue

                for tweet in tweets:
                    tweet_id = tweet.get("id")
                    if last_tweet_ids[username] >= tweet_id:
                        continue

                    text = tweet.get("text", "")
                    if not any(kw in text.lower() for kw in KEYWORDS):
                        continue

                    codes = re.findall(r'\b[A-Z0-9]{6,20}\b', text.upper())
                    codes_str = ""
                    if codes:
                        codes_str = "\n\n🧧 <b>КОДЫ В ПОСТЕ:</b>\n" + "\n".join([f"<code>{c}</code>" for c in codes])

                    message = f"""
🔥 <b>НОВАЯ РАЗДАЧА / БОКС / ЗАГАДКА</b> от @{username}

{text}

{codes_str}
🕒 {datetime.now().strftime('%d.%m %H:%M')}
🔗 https://x.com/{username}/status/{tweet_id}
                    """.strip()

                    send_to_telegram(message)
                    print(f"✅ Отправлено @{username} – {datetime.now().strftime('%H:%M:%S')}")

                    last_tweet_ids[username] = tweet_id

            except Exception as e:
                print(f"⚠️ Ошибка при обработке @{username}: {e}")

            time.sleep(2)

        time.sleep(1)

if __name__ == "__main__":
    main()
