import os
import sys
import time
import requests
import re
import random
import traceback
from datetime import datetime
from collections import defaultdict

# ====================== ТВОИ НАСТРОЙКИ ======================
API_KEY = os.getenv("TWITTER_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID_STR = os.getenv("CHAT_ID")

# Проверка наличия переменных
if not API_KEY:
    print("❌ Ошибка: не задана переменная TWITTER_API_KEY", flush=True)
    sys.exit(1)
if not TELEGRAM_TOKEN:
    print("❌ Ошибка: не задана переменная TELEGRAM_TOKEN", flush=True)
    sys.exit(1)
if not CHAT_ID_STR:
    print("❌ Ошибка: не задана переменная CHAT_ID", flush=True)
    sys.exit(1)
try:
    CHAT_ID = int(CHAT_ID_STR)
except ValueError:
    print(f"❌ Ошибка: CHAT_ID должно быть числом, получено {CHAT_ID_STR}", flush=True)
    sys.exit(1)

# Группы аккаунтов
GROUPS = {
    "frequent": {
        "accounts": ["heyibinance", "binancezh", "binance_boxses"],
        "interval": 1800  # 30 минут
    },
    "medium": {
        "accounts": ["Bybit_Official", "Bybit_ZH", "binance"],
        "interval": 17280  # 5 раз в сутки
    },
    "rare": {
        "accounts": ["benbybit", "BybitAnnouncements", "BybitSouthAsia", "BybitPlus"],
        "interval": 86400  # 1 раз в сутки
    }
}

# Расширенные ключевые слова
KEYWORDS = [
    # Базовые английские
    "box", "boxes", "mystery box", "crypto box", "lucky bag", "red packet",
    "giveaway", "code", "redeem", "gift", "bonus", "special", "exclusive",
    "event", "campaign", "prize", "reward", "claim", "free",
    
    # Русские
    "бокс", "раздача", "загадка", "код", "подарок", "сюрприз", "приз",
    "розыгрыш", "лотерея",
    
    # Китайские (иероглифы)
    "币安",           # Binance
    "活动",           # мероприятие/акция
    "红包",           # красный конверт (red packet)
    "口令",           # пароль/код
    "抽奖",           # лотерея/розыгрыш
    "礼盒",           # подарочная коробка (box)
    "礼包",           # подарочный набор
    "福利",           # бонус/подарок
    "盲盒",           # слепая коробка (mystery box)
    "福袋",           # lucky bag
    "大奖",           # главный приз
    "奖励",           # награда
    "惊喜",           # сюрприз
    "邀请",           # приглашение
    "注册",           # регистрация
    "赠送",           # подарок
    "圣诞愿望",       # рождественское желание (популярный хештег) [citation:1]
    "贺岁",           # новогоднее поздравление
    "限时",           # ограниченное время
    
    # Китайские для загадок
    "谜语",           # загадка (riddle)
    "猜谜",           # угадайка
    "答案",           # ответ
    "解密",           # разгадка
    "提示",           # подсказка
    
    # Хештеги (часто содержат ключи)
    "#BinanceWish",  # популярный хештег акций [citation:2]
    "#BinanceBox",
    "#BybitRedPacket",
    "#Giveaway",
    
    # Общие
    "win", "winner", "participate", "join now", "limited", "exclusive"
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

# Инициализация времени последней проверки со случайным смещением
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
            print(f"📥 @{username}: получил {len(tweets)} твитов", flush=True)
            for t in tweets:
                text = t.get('text', '')[:100]
                print(f"   📝 {text}...", flush=True)
            return tweets
        else:
            print(f"⚠️ Ошибка API для @{username}: {resp.status_code} – {resp.text[:100]}", flush=True)
            return []
    except Exception as e:
        print(f"⚠️ Ошибка запроса для @{username}: {e}", flush=True)
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
            print(f"⚠️ Telegram ошибка: {r.status_code} – {r.text[:100]}", flush=True)
    except Exception as e:
        print(f"⚠️ Ошибка отправки в Telegram: {e}", flush=True)

def main():
    print(f"[{datetime.now()}] 🔥 Бот запущен на Railway", flush=True)
    print(f"📊 Мониторинг {len(TARGET_ACCOUNTS)} аккаунтов:", flush=True)
    for acc in TARGET_ACCOUNTS:
        print(f"   - @{acc} (интервал: {get_interval_for_user(acc)} сек)", flush=True)

    # Отправляем тестовое сообщение
    send_to_telegram("✅ Бот запущен и начал мониторинг")

    print("🔄 Вход в основной цикл...", flush=True)

    while True:
        try:
            now = time.time()
            for username in TARGET_ACCOUNTS:
                interval = get_interval_for_user(username)
                if now - last_check_time[username] < interval:
                    continue

                last_check_time[username] = now
                print(f"\n⏳ Проверка @{username} в {datetime.now().strftime('%H:%M:%S')}", flush=True)

                tweets = get_latest_tweets(username)
                if not tweets:
                    time.sleep(2)
                    continue

                for tweet in tweets:
                    tweet_id = tweet.get("id")
                    if last_tweet_ids[username] >= tweet_id:
                        print(f"   ⏭️ Твит {tweet_id} уже обработан", flush=True)
                        continue

                    text = tweet.get("text", "")
                    if not any(kw in text.lower() for kw in KEYWORDS):
                        print(f"   ⏭️ Твит {tweet_id} не содержит ключевых слов", flush=True)
                        continue

                    print(f"   ✅ Твит {tweet_id} подходит! Отправляю...", flush=True)
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
        except Exception as e:
            print(f"🔥 Критическая ошибка в основном цикле: {e}", flush=True)
            traceback.print_exc(file=sys.stdout)
            time.sleep(10)  # пауза перед повтором

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"💥 Необработанная ошибка: {e}", flush=True)
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)


