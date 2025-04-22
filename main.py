# Bot Plan A Nhất Thống – Gate.io Volume Spike Strategy (All-in 99 USDT)
# Tự động tìm coin mạnh nhất theo volume realtime, trade Spot Gate.io, TP/SL thông minh

import requests
import hmac
import hashlib
import time
import datetime
import os
import json

# ===== CONFIG =====
API_KEY = os.getenv("GATE_API_KEY", "d97047b3bc7c5a1565a31d43f80b68ee")
SECRET_KEY = os.getenv("GATE_API_SECRET", "8fbbeb3092520127ff1468e959515b651780408c164ed28f88eaace75bf669ec")
CHAT_ID = os.getenv("CHAT_ID", "755523445")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7290587071:AAGdDyPtKKs_v2X48zaVM9-OjobhcztNnsk")
BASE_URL = "https://api.gateio.ws/api/v4"

# ===== TELEGRAM =====
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg})
    except: pass

# ===== GATE SIGNING =====
def gate_sign(method, url, payload=''):
    t = str(int(time.time()))
    hashed_payload = hashlib.sha512(payload.encode()).hexdigest() if payload else ''
    message = f'{t}\n{method}\n{url}\n{hashed_payload}\n'
    signature = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha512).hexdigest()
    headers = {
        'KEY': API_KEY,
        'Timestamp': t,
        'SIGN': signature,
        'Content-Type': 'application/json'
    }
    return headers

# ===== GET BALANCE =====
def get_balance():
    url = "/spot/accounts"
    headers = gate_sign('GET', url)
    try:
        res = requests.get(BASE_URL + url, headers=headers).json()
        for b in res:
            if b['currency'] == 'usdt':
                return float(b['available'])
    except: pass
    return 0.0

# ===== GET TOP VOLUME COINS =====
def get_top_coin():
    try:
        url = f"{BASE_URL}/spot/tickers"
        res = requests.get(url).json()
        filtered = [i for i in res if i['currency_pair'].endswith('_USDT') and float(i['base_volume']) > 1000000]
        sorted_data = sorted(filtered, key=lambda x: float(x['base_volume']), reverse=True)
        return sorted_data[0]['currency_pair'] if sorted_data else None
    except Exception as e:
        send_telegram(f"[Bot A] Lỗi khi quét coin: {e}")
        return None

# ===== PLACE ORDER =====
def place_order(pair, side, amount):
    url = "/spot/orders"
    data = {
        "currency_pair": pair,
        "type": "market",
        "side": side,
        "amount": str(amount)
    }
    payload = json.dumps(data)
    headers = gate_sign("POST", url, payload)
    try:
        return requests.post(BASE_URL + url, headers=headers, data=payload).json()
    except:
        return {}

# ===== MAIN LOOP =====
def bot_loop():
    holding = False
    entry_price = 0
    quantity = 0
    symbol = ""
    tp = sl = 0

    while True:
        try:
            if not holding:
                symbol = get_top_coin()
                if not symbol:
                    time.sleep(30)
                    continue

                price_data = requests.get(f"{BASE_URL}/spot/tickers?currency_pair={symbol}").json()
                entry_price = float(price_data['last'])
                usdt = get_balance()
                quantity = round(usdt / entry_price, 4)

                tp = round(entry_price * 1.07, 6)   # TP 7%
                sl = round(entry_price * 0.965, 6)  # SL 3.5%

                place_order(symbol, "buy", quantity)
                send_telegram(f"🟢 MUA {symbol} tại {entry_price}\n🎯 TP: {tp} | 🛡️ SL: {sl}")
                holding = True

            else:
                price = float(requests.get(f"{BASE_URL}/spot/tickers?currency_pair={symbol}").json()['last'])
                now = datetime.datetime.now().strftime("%H:%M:%S")

                if price >= tp:
                    place_order(symbol, "sell", quantity)
                    send_telegram(f"✅ CHỐT LỜI {symbol} tại {price} | TP đạt +7% | {now}")
                    holding = False
                elif price <= sl:
                    place_order(symbol, "sell", quantity)
                    send_telegram(f"❌ CẮT LỖ {symbol} tại {price} | SL -3.5% | {now}")
                    holding = False

            time.sleep(60)
        except Exception as e:
            send_telegram(f"[Bot A] Lỗi: {e}")
            time.sleep(60)

if __name__ == '__main__':
    bot_loop()
