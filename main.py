# Bot A – Plan A Pro phiên bản Telegram + Spot MEXC (FET – 25 USDT)
# Tự động phân tích – đặt lệnh – chốt lời – báo Telegram – dùng API MEXC v1

import time
import requests
import hmac
import hashlib
import datetime
import os

# ====== CONFIG ======
API_KEY = os.getenv("API_KEY", "mx0vgl72I1Bi63sS6h")
SECRET_KEY = os.getenv("SECRET_KEY", "a60ced2b7abc4f7783cbabf2090e86f8")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7290587071:AAGdDyPtKKs_v2X48zaVM9-OjobhcztNnsk")
CHAT_ID = os.getenv("CHAT_ID", "755523445")
SYMBOL = "FETUSDT"  # MEXC dùng FETUSDT không có dấu gạch dưới

# ====== TELEGRAM ======
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data)
    except:
        pass

# ====== KLINE API v1 ======
def get_kline():
    try:
        url = f"https://www.mexc.com/api/v1/klines?symbol={SYMBOL}&interval=1m&limit=20"
        res = requests.get(url)
        data = res.json()
        if not isinstance(data, list):
            print("🔴 Dữ liệu kline không phải list!", flush=True)
            return []
        if len(data) < 20:
            print(f"🔴 Chỉ nhận được {len(data)} nến! Cần >=20.", flush=True)
            return []
        return data
    except Exception as e:
        print("🔴 LỖI kline:", e, flush=True)
        return []

# ====== CHỈ BÁO ======
def calculate_indicators(data):
    closes = [float(i[4]) for i in data]
    volumes = [float(i[5]) for i in data]

    gains = []
    losses = []
    for i in range(1, 15):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))

    avg_gain = sum(gains) / 14
    avg_loss = sum(losses) / 14
    rs = avg_gain / avg_loss if avg_loss != 0 else 0.01
    rsi = 100 - (100 / (1 + rs))

    ma5 = sum(closes[-5:]) / 5
    ma20 = sum(closes[-20:]) / 20
    avg_vol = sum(volumes[-4:-1]) / 3
    vol_spike = volumes[-1] > avg_vol * 1.3

    return closes[-1], rsi, ma5, ma20, vol_spike

# ====== ĐẶT LỆNH MEXC SPOT ======
def place_order(side, quantity):
    try:
        url = "https://api.mexc.com/api/v3/order"
        timestamp = int(time.time() * 1000)
        params = {
            "symbol": SYMBOL,
            "side": side,
            "type": "MARKET",
            "quantity": quantity,
            "timestamp": timestamp
        }
        query = "&".join([f"{k}={params[k]}" for k in sorted(params)])
        signature = hmac.new(SECRET_KEY.encode(), query.encode(), hashlib.sha256).hexdigest()
        full_url = url + "?" + query + f"&signature={signature}"
        headers = {"X-MEXC-APIKEY": API_KEY}
        response = requests.post(full_url, headers=headers)
        return response.json()
    except:
        return {}

# ====== GET SỐ DƯ ======
def get_balance():
    try:
        url = "https://api.mexc.com/api/v3/account"
        timestamp = int(time.time() * 1000)
        params = {"timestamp": timestamp}
        query = "&".join([f"{k}={params[k]}" for k in sorted(params)])
        signature = hmac.new(SECRET_KEY.encode(), query.encode(), hashlib.sha256).hexdigest()
        full_url = url + "?" + query + f"&signature={signature}"
        headers = {"X-MEXC-APIKEY": API_KEY}
        res = requests.get(full_url, headers=headers).json()
        for b in res.get("balances", []):
            if b['asset'] == 'USDT':
                return float(b['free'])
        return 0.0
    except:
        return 0.0

# ====== TÍNH TP/SL ======
def calculate_tp_sl(entry):
    tp = round(entry * 1.07, 6)
    sl = round(entry * 0.96, 6)
    return tp, sl

# ====== CHẠY BOT ======
if __name__ == '__main__':
    holding = False
    entry = tp = sl = 0
    qty = 0
    usdt_used = 0

    while True:
        try:
            kline = get_kline()
            if not kline or len(kline) < 20:
                send_telegram("⚠️ [Bot A] Không đủ dữ liệu kline từ API v1. Đợi thêm...")
                time.sleep(60)
                continue

            price, rsi, ma5, ma20, vol_spike = calculate_indicators(kline)
            now = datetime.datetime.now().strftime("%H:%M:%S")

            if not holding and rsi < 38 and ma5 > ma20 and vol_spike:
                entry = price
                tp, sl = calculate_tp_sl(entry)
                usdt_used = get_balance()
                qty = round(usdt_used / entry, 2)
                place_order("BUY", qty)
                send_telegram(f"""🟢 [Bot A] {now} MUA FET\nGiá: {entry}\n🎯 TP: {tp} | 🛡️ SL: {sl}""")
                holding = True
            elif holding:
                if price >= tp:
                    place_order("SELL", qty)
                    send_telegram(f"✅ [Bot A] {now} CHỐT LỜI tại {price} | Lãi ~{(price-entry)/entry*100:.2f}%")
                    holding = False
                elif price <= sl:
                    place_order("SELL", qty)
                    send_telegram(f"❌ [Bot A] {now} CẮT LỖ tại {price} | Lỗ ~{(price-entry)/entry*100:.2f}%")
                    holding = False

            time.sleep(60)
        except Exception as e:
            send_telegram(f"[Bot A] Lỗi: {e}")
            time.sleep(60)
