import MetaTrader5 as mt5
import time
import json
import config
from utils.helpers import calculate_ema, fetch_latest_gold_news, fetch_high_impact_news, ask_ai

def monitor_market():
    if not mt5.initialize(login=config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER):
        print("Gagal konek ke MT5!")
        return

    print(f"📡 [WATCHER] Memantau Momentum {config.SYMBOL}...")
    threshold = 1.0  # Threshold untuk alarm momentum
    
    try:
        while True:
            rates = mt5.copy_rates_from_pos(config.SYMBOL, mt5.TIMEFRAME_M5, 0, 50)
            if rates is not None and len(rates) > 20:
                prices = [r['close'] for r in rates]
                ema9 = calculate_ema(prices, 9)
                ema21 = calculate_ema(prices, 21)
                curr_price = prices[-1]

                if ema9 and ema21:
                    diff = abs(ema9 - ema21)
                    if diff >= threshold:
                        print(f"🚨 MOMENTUM DETECTED: Diff {diff:.2f}")
                        
                        # ALARM MENGGUNAKAN AI (PENGGANTI OPENCLAW AGENT)
                        news = fetch_latest_gold_news()
                        high_impact = fetch_high_impact_news()
                        prompt = (
                            f"URGENT: Momentum Gold {config.SYMBOL} terdeteksi.\n"
                            f"Price: {curr_price} | EMA Diff: {diff:.2f}\n"
                            f"News: {news}\n{high_impact}\n"
                            f"Berikan peringatan singkat 1 kalimat sebagai AI Assistant."
                        )
                        res = ask_ai(prompt)
                        if res:
                            # In a real app we could use system notification, here we just print
                            print(f"🧠 AI ALERT: {res.get('response', '...')}")

            time.sleep(60)
    except KeyboardInterrupt: print("Watcher Stopped.")
    finally: mt5.shutdown()

if __name__ == "__main__":
    monitor_market()
