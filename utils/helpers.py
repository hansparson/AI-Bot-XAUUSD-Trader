import os
import json
import urllib.request
import xml.etree.ElementTree as ET
import MetaTrader5 as mt5
import config
from datetime import datetime, time, timedelta

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
def calculate_atr(rates, period=14):
    """Menghitung Average True Range (ATR)"""
    if len(rates) < period + 1:
        return None
    tr_list = []
    for i in range(1, len(rates)):
        high = rates[i]['high']
        low = rates[i]['low']
        prev_close = rates[i-1]['close']
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_list.append(tr)
    
    # Simple Moving Average untuk ATR awal
    atr = sum(tr_list[:period]) / period
    for i in range(period, len(tr_list)):
        atr = (atr * (period - 1) + tr_list[i]) / period
    return round(atr, 5)

def get_market_regime(prices):
    """Mendeteksi apakah pasar sedang Trending atau Sideways"""
    if len(prices) < 50:
        return "UNKNOWN"
    
    ema20 = calculate_ema(prices, 20)
    ema50 = calculate_ema(prices, 50)
    
    # Hitung ADX sederhana atau deviasi harga
    # Kita gunakan jarak antara EMA 20 dan 50 sebagai indikator tren
    diff = abs(ema20 - ema50)
    avg_price = sum(prices[-10:]) / 10
    
    # Jika selisih EMA > 0.1% dari harga, anggap trending
    if diff > (avg_price * 0.001):
        return "TRENDING"
    else:
        return "SIDEWAYS"

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

def is_high_impact_news_active():
    """Mengecek apakah ada berita high impact yang aktif saat ini"""
    news = fetch_high_impact_news()
    return "⚠️ HIGH IMPACT" in news

def get_mtf_trends(symbol):
    """Mengambil tren dari timeframe lebih tinggi (M15 dan H1)"""
    result = {}
    for tf_name, tf_const in [("M15", mt5.TIMEFRAME_M15), ("H1", mt5.TIMEFRAME_H1)]:
        try:
            rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, 100)
            if rates is None or len(rates) < 50:
                result[tf_name] = "N/A"
                continue
            prices = [r['close'] for r in rates]
            ema50 = calculate_ema(prices, 50)
            ema200 = calculate_ema(prices, 200) # Jika data cukup
            
            last_price = prices[-1]
            if ema50 and last_price > ema50:
                result[tf_name] = "BULLISH"
            elif ema50 and last_price < ema50:
                result[tf_name] = "BEARISH"
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

def get_spread(symbol):
    """Mengambil spread saat ini (dalam points)"""
    info = mt5.symbol_info(symbol)
    return info.spread if info else 999

def is_valid_rejection(rates, tech_signal):
    """Memeriksa apakah candle terakhir adalah rejection valid (Wick > Body)"""
    if len(rates) < 2:
        return False
    
    last = rates[-1]
    body = abs(last['close'] - last['open'])
    candle_range = last['high'] - last['low']
    
    if candle_range == 0:
        return False

    # Hitung ATR untuk filter volume (Special Ops: 20% ATR)
    atr = calculate_atr(rates, 14)
    if not atr or candle_range < (atr * 0.2): 
        return False 

    if tech_signal == "BUY":
        # Pinbar Bullish: Wick bawah panjang
        wick_bottom = min(last['open'], last['close']) - last['low']
        return wick_bottom > body
    elif tech_signal == "SELL":
        # Pinbar Bearish: Wick atas panjang
        wick_top = last['high'] - max(last['open'], last['close'])
        return wick_top > body
    
    return False

def get_equity_drawdown():
    """Menghitung drawdown saat ini berdasarkan Balance vs Equity"""
    acc = mt5.account_info()
    if not acc:
        return 0.0
    if acc.balance <= 0:
        return 0.0
    drawdown = (acc.balance - acc.equity) / acc.balance * 100
    return round(max(0, drawdown), 2)

def is_equity_curve_healthy():
    """Mengecek apakah performa 3 hari terakhir memburuk (sequential loss days)"""
    now = datetime.now()
    results = []
    for i in range(3):
        day_start = datetime(now.year, now.month, now.day) - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        
        deals = mt5.history_deals_get(day_start, day_end)
        if deals:
            day_pnl = sum((d.profit + d.commission + d.swap) for d in deals if d.entry == mt5.DEAL_ENTRY_OUT)
            results.append(day_pnl)
        else:
            results.append(0.0)
            
    # Jika 3 hari terakhir semuanya negatif
    if len(results) == 3 and all(r < 0 for r in results):
        return False
    return True

def can_resume_trading():
    """Mengecek apakah kondisi pasar sudah 'tenang' untuk resume setelah drawdown"""
    # 1. Tidak ada High Impact News
    if is_high_impact_news_active():
        return False
    
    # 2. Volatility (ATR) dalam batas wajar (tidak sedang spike gila)
    rates = mt5.copy_rates_from_pos(config.SYMBOL, mt5.TIMEFRAME_M1, 0, 30)
    if rates is not None:
        atr = calculate_atr(rates, 14)
        if atr and atr > 1.5: # Threshold arbitrer untuk XAUUSD 'gila'
            return False
            
    return True

def ask_ai(prompt_text, mode_override=None):
    """Fungsi AI Hybrid: Bisa Lokal (Ollama) atau Cloud (Gemini)"""
    target_mode = mode_override if mode_override else config.AI_MODE
    
    if target_mode == "CLOUD":
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
