import os
import time
import requests
import re
import random
from datetime import datetime
from collections import defaultdict

# ====================== ТВОИ НАСТРОЙКИ ======================
API_KEY = os.getenv("TWITTER_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID", "0"))

GROUPS = {
    "frequent": {
        "accounts": ["heyibinance", "binancezh", "binance_boxses"],
        "interval": 1800  # 30 минут
    },
    "medium": {
        "accounts": ["Bybit_Official", "Bybit_ZH", "binance"],
        "interval": 17280  # 5 раз/сутки
    },
    "rare": {
        "accounts": ["benbybit", "BybitAnnouncements", "BybitSouthAsia", "BybitPlus"],
        "interval": 86400  # 1 раз/сутки
    }
}

# Расширенный список ключевых слов – добавь то, что видишь в твитах
KEYWORDS = [
    "box", "бокс", "crypto box", "mystery box", "福袋", "red packet",
    "红包", "口令", "загадка", "riddle", "code", "код", "redeem",
    "big gift", "special", "giveaway", "event", "claim", "bonus", "free",
    "lucky", "抽奖", "奖励", "礼包"
]
# =============================================================

TARGET_ACCOUNTS = []
for group in GROUPS.values():
    TARGET_ACCOUNTS.extend(group["accounts"])

last_tweet_ids = defaultdict(int)
last_check_time = defaultdict(float)

def get_interval_for_user(username):
    for group in GROUPS.values():
        if username in group["accounts"]:
            return group["interval"]
    return 1800

current_time = time.time()
for username in TARGET_ACCOUNTS:
    interval = get_interval_for_user(username)
    last_check_time[username] = current_time - random.uniform(0, interval)

def get_latest_tweets(username):
    url = "https://api.twitterapi.io/twitter/user/latest_tweets"
    headers = {"x-api-key": API_KEY}
    params = {"userName": username, "count": 5}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            tweets = data.get("tweets", [])
            print(f"📥 @{username}: получил {len(tweets)} твитов")
            for t in tweets:
                print(f"   📝 {t.get('text', '')[:100]}...")
            return tweets
        else:
            print(f"⚠️ Ошибка API для @{username}: {resp.status_code} – {resp.text[:100]}")
            return []
    except Exception as e:
        print(f"⚠️ Ошибка запроса для @{username}: {e}")
        return []

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            print(f"⚠️ Telegram ошибка: {r.status_code} – {r.text[:100]}")
    except Exception as e:
        print(f"⚠️ Ошибка отправки в Telegram: {e}")

def main():
    print(f"[{datetime.now()}] 🔥 Бот запущен на Railway")
    print(f"📊 Мониторинг {len(TARGET_ACCOUNTS)} аккаунтов:")
    for acc in TARGET_ACCOUNTS:
        print(f"   - @{acc} (интервал: {get_interval_for_user(acc)} сек)")

    # 🔽 Если хочешь отключить тестовое сообщение, закомментируй следующую строку
    send_to_telegram("✅ Бот запущен и начал мониторинг")

    while True:
        now = time.time()
        for username in TARGET_ACCOUNTS:
            interval = get_interval_for_user(username)
            if now - last_check_time[username] < interval:
                continue

            last_check_time[username] = now
            print(f"\n⏳ Проверка @{username} в {datetime.now().strftime('%H:%M:%S')}")

            tweets = get_latest_tweets(username)
            if not tweets:
                time.sleep(2)
                continue

            for tweet in tweets:
                tweet_id = tweet.get("id")
                if last_tweet_ids[username] >= tweet_id:
                    print(f"   ⏭️ Твит {tweet_id} уже обработан")
                    continue

                text = tweet.get("text", "")
                if not any(kw in text.lower() for kw in KEYWORDS):
                    print(f"   ⏭️ Твит {tweet_id} не содержит ключевых слов")
                    continue

                print(f"   ✅ Твит {tweet_id} подходит! Отправляю...")
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
                last_tweet_ids[username] = tweet_id

            time.sleep(2)

        time.sleep(1)

if __name__ == "__main__":
    main()
