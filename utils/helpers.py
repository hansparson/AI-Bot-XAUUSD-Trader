import os
import json
import urllib.request
import xml.etree.ElementTree as ET
import MetaTrader5 as mt5
import config
from datetime import datetime, time

def calculate_ema(prices, period):
    """Menghitung Exponential Moving Average (EMA)"""
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price * k) + (ema * (1 - k))
    return round(ema, 5)

def calculate_rsi(prices, period=14):
    """Menghitung Relative Strength Index (RSI)"""
    if len(prices) < period + 1:
        return None
    
    gains = []
    losses = []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        gains.append(max(0, change))
        losses.append(max(0, -change))
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    if avg_loss == 0:
        return 100
    
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    if avg_loss == 0:
        return 100
        
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)

def fetch_latest_gold_news():
    """Mengambil berita fundamental emas terbaru"""
    try:
        url = "https://finance.yahoo.com/rss/commodities"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            rss_data = response.read()
            root = ET.fromstring(rss_data)
            headlines = []
            for item in root.findall('./channel/item')[:3]: 
                headlines.append(item.find('title').text)
            return " | ".join(headlines)
    except Exception as e:
        return "Sinyal Fundamental tidak tersedia."

def fetch_high_impact_news():
    """Mengambil event kalender ekonomi (High Impact USD)"""
    try:
        url = "https://rss.fxstreet.com/news"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            rss_data = response.read()
            root = ET.fromstring(rss_data)
            items = root.findall('./channel/item')[:5]
            keywords = ['fed', 'fomc', 'cpi', 'nonfarm', 'gdp', 'inflation', 'rate', 'powell', 'treasury', 'employment']
            high_impact = []
            for item in items:
                title_el = item.find('title')
                if title_el is not None and title_el.text:
                    title_low = title_el.text.lower()
                    if any(kw in title_low for kw in keywords):
                        high_impact.append(title_el.text.strip())
            if high_impact:
                return "⚠️ HIGH IMPACT: " + " | ".join(high_impact[:3])
            return "Tidak ada event high impact terdeteksi."
    except:
        return "Kalender ekonomi tidak tersedia."

def get_mtf_trends(symbol):
    """Mengambil tren dari timeframe lebih tinggi (M15 dan H1)"""
    result = {}
    for tf_name, tf_const in [("M15", mt5.TIMEFRAME_M15), ("H1", mt5.TIMEFRAME_H1)]:
        try:
            rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, 30)
            if rates is None or len(rates) < 22:
                result[tf_name] = "N/A"
                continue
            prices = [r['close'] for r in rates]
            ema9 = calculate_ema(prices, 9)
            ema21 = calculate_ema(prices, 21)
            if ema9 and ema21:
                result[tf_name] = "BULLISH" if ema9 > ema21 else "BEARISH"
            else:
                result[tf_name] = "N/A"
        except:
            result[tf_name] = "N/A"
    return result

def get_filling_mode(symbol):
    """Mendeteksi filling mode yang didukung broker"""
    # Fokus ke FOK (MIFX) atau IOC (MetaQuotes)
    return mt5.ORDER_FILLING_FOK

def get_account_risk(min_margin_level=300.0):
    """Mengambil status keamanan akun"""
    account_info = mt5.account_info()
    if account_info:
        margin_level = getattr(account_info, "margin_level", 0.0)
        return {
            "equity": account_info.equity,
            "margin_level": margin_level,
            "can_trade": margin_level > min_margin_level or margin_level == 0.0
        }
    return None

def is_market_open(symbol):
    """Mengecek apakah pasar sedang buka (Live) atau tutup via status broker & kesegaran harga"""
    info = mt5.symbol_info(symbol)
    if info is None:
        return False
        
    # 1. Cek Mode Trading (Harus FULL)
    # trade_mode: 0=disabled, 1=long only, 2=short only, 3=close only, 4=full
    is_active = info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL
    
    # 2. Cek Kesegaran Harga (Timestamp)
    # Jika harga terakhir sudah lebih dari 10 menit (600 detik) yang lalu, pasar dianggap offline
    # Kita menggunakan mt5.symbol_info_tick untuk mendapatkan waktu tick terakhir
    tick = mt5.symbol_info_tick(symbol)
    if tick:
        # Kita bandingkan waktu sekarang (GMT) vs waktu tick (GMT Server)
        # Note: Ini mengasumsikan PC User punya jam yang sinkron
        import time
        current_time = int(time.time())
        # Kita beri toleransi offset server vs local (misal server GMT+2, local GMT+7 -> selisih 18000s)
        # Namun pendekatan paling aman: Jika harga tidak berubah > 20 menit, anggap tutup.
        # Karena Gold tutup 1 jam tiap hari, 20 menit cukup aman.
        if (current_time - tick.time) > 43200: # 12 Jam (Safe threshold for weekend/market close)
            # Selisih besar biasanya karena weekend
            return False

    return is_active

def ask_ai(prompt_text):
    """Fungsi AI Hybrid: Bisa Lokal (Ollama) atau Cloud (Gemini)"""
    if config.AI_MODE == "CLOUD":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.CLOUD_MODEL}:generateContent?key={config.GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2
            }
        }
        try:
            req_obj = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'))
            req_obj.add_header('Content-Type', 'application/json')
            with urllib.request.urlopen(req_obj, timeout=30) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
                usage = res_data.get('usageMetadata', {})
                return {"response": raw_text, "usage": usage}
        except Exception as e:
            print(f"❌ Gemini Error: {e}")
            return None
    else:
        url = config.AI_URL
        payload = {
            "model": config.LOCAL_MODEL, "prompt": prompt_text, "stream": False,
            "options": {"temperature": 0.2, "num_predict": 250}, "format": "json"
        }
        try:
            req_obj = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'))
            req_obj.add_header('Content-Type', 'application/json')
            with urllib.request.urlopen(req_obj, timeout=30) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                # Ollama typical response doesn't have metadata in 'format: json' mode sometimes
                # but we can simulate it if needed.
                return {"response": res_data.get("response", ""), "usage": {}}
        except Exception as e:
            print(f"❌ Ollama Error: {e}")
            return None

def close_positions_by_type(symbol, target_type):
    """Menutup posisi berdasarkan tipe (BUY/SELL)"""
    positions = mt5.positions_get(symbol=symbol)
    if positions:
        for pos in positions:
            if pos.type == target_type:
                tick = mt5.symbol_info_tick(symbol)
                order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
                price = tick.bid if pos.type == mt5.POSITION_TYPE_BUY else tick.ask
                
                request = {
                    "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": pos.volume,
                    "type": order_type, "position": pos.ticket, "price": price,
                    "deviation": 20, "magic": config.MAGIC_NUMBER, "comment": "Close by Helper",
                    "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC,
                }
                mt5.order_send(request)

def get_market_session():
    """Mendeteksi sesi pasar (GMT+0 / UTC)"""
    # MT5 Server time usually follows specific offsets, but let's use UTC for logic
    now_utc = datetime.utcnow().time()
    
    if time(0, 0) <= now_utc < time(8, 0):
        return "ASIA (Tokyo/Sydney)"
    elif time(8, 0) <= now_utc < time(13, 0):
        return "LONDON (Europe)"
    elif time(13, 0) <= now_utc < time(21, 0):
        return "NEW YORK (US)"
    else:
        return "GAP (Late US/Early Asia)"

def get_daily_pnl():
    """Menghitung total profit/loss hari ini dari riwayat trading MT5"""
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)
    
    # Ambil deals dari awal hari ini
    history_deals = mt5.history_deals_get(today_start, now)
    if history_deals is None:
        return 0.0
        
    total_pnl = 0.0
    for deal in history_deals:
        # Filter deal entry: deal.entry=1 (OUT) atau deal.entry=0 (IN, tapi IN tidak ada profit)
        if deal.entry == mt5.DEAL_ENTRY_OUT:
            total_pnl += (deal.profit + deal.commission + deal.swap + deal.fee)
            
    return round(total_pnl, 2)
