# Bot A – Plan A Pro phiên bản Telegram + Spot Gate (Volume Bot – 99 USDT)
# Tự động tìm coin volume cao theo thời gian thực – vào lệnh duy nhất 1 coin để nhất thống Plan A

import time
import requests
import datetime
from flask import Flask
import multiprocessing
import os

# ====== CONFIG ======
API_KEY = os.getenv("API_KEY", "d97047b3bc7c5a1565a31d43f80b68ee")
API_SECRET = os.getenv("API_SECRET", "8fbbeb3092520127ff1468e959515b651780408c164ed28f88eaace75bf669ec")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7290587071:AAGdDyPtKKs_v2X48zaVM9-OjobhcztNnsk")
CHAT_ID = os.getenv("CHAT_ID", "755523445")

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot A – Volume Bot đang chạy."

# ====== TELEGRAM ======
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data)
    except:
        pass

# ====== TÌM COIN VOLUME CAO NHẤT ======
def find_top_volume_coin():
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        res = requests.get(url)
        data = res.json()
        top = sorted(
            [c for c in data if isinstance(c, dict) and c.get("quote_currency") == "usdt" and float(c.get("base_volume", 0)) > 0],
            key=lambda x: float(x["quote_volume"]),
            reverse=True
        )
        return top[0]["currency_pair"] if top else None
    except Exception as e:
        send_telegram(f"[Bot A] Lỗi khi quét coin: {e}")
        return None

# ====== LẤY GIÁ COIN ======
def get_price(symbol):
    try:
        url = f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={symbol}"
        res = requests.get(url, timeout=10)
        data = res.json()
        return float(data["last"])
    except Exception as e:
        send_telegram(f"[Bot A] Lỗi khi lấy giá {symbol}: {e}")
        return None

# ====== GIẢ LẬP VÀO LỆNH ======
def place_order(symbol, side, amount):
    # Đây là mock để test logic, chưa gọi thật Gate API
    print(f"Đặt lệnh {side} {amount} {symbol}")
    return True

# ====== CHẠY BOT ======
def bot_loop():
    holding = False
    symbol = ""
    entry = tp = sl = 0

    while True:
        try:
            if not holding:
                symbol = find_top_volume_coin()
                if not symbol:
                    time.sleep(60)
                    continue
                
                entry = get_price(symbol)
                if not entry:
                    time.sleep(60)
                    continue

                tp = round(entry * 1.06, 6)
                sl = round(entry * 0.97, 6)
                place_order(symbol, "buy", 99 / entry)
                send_telegram(f"🟢 [Bot A] MUA {symbol} tại {entry}\n🎯 TP: {tp} | 🛡️ SL: {sl}")
                holding = True
            else:
                price = get_price(symbol)
                if not price:
                    time.sleep(60)
                    continue
                now = datetime.datetime.now().strftime("%H:%M:%S")
                if price >= tp:
                    place_order(symbol, "sell", 99 / entry)
                    send_telegram(f"✅ [Bot A] {symbol} CHỐT LỜI tại {price} | Lãi ~{(price-entry)/entry*100:.2f}%")
                    holding = False
                elif price <= sl:
                    place_order(symbol, "sell", 99 / entry)
                    send_telegram(f"❌ [Bot A] {symbol} CẮT LỖ tại {price} | Lỗ ~{(price-entry)/entry*100:.2f}%")
                    holding = False
            time.sleep(60)
        except Exception as e:
            send_telegram(f"[Bot A] Lỗi: {e}")
            time.sleep(60)

# ====== KHỞI CHẠY ======
if __name__ == '__main__':
    multiprocessing.Process(target=bot_loop).start()
    multiprocessing.Process(target=lambda: app.run(host='0.0.0.0', port=8081)).start()
