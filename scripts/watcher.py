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
                    trend_icon = "📈 UP" if ema9 > ema21 else "📉 DOWN"
                    now = time.strftime("%H:%M:%S")
                    print(f"[{now}] Price: {curr_price:.2f} | EMA9: {ema9:.2f} | EMA21: {ema21:.2f} | Trend: {trend_icon}")

                    if diff >= threshold:
                        print(f"🚨 MOMENTUM! Diff: {diff:.2f}")
                        news = fetch_latest_gold_news()
                        high_impact = fetch_high_impact_news()
                        prompt = (
                            f"URGENT: Momentum Gold {config.SYMBOL} terdeteksi.\n"
                            f"Price: {curr_price} | Trend: {trend_icon} | EMA Diff: {diff:.2f}\n"
                            f"News: {news}\n{high_impact}\n"
                            f"Berikan peringatan singkat 1 kalimat sebagai AI Assistant Profesional."
                        )
                        res = ask_ai(prompt)
                        if res:
                            alert_txt = res.get('response', '...')
                            print(f"🧠 AI ALERT: \"{alert_txt}\"")
                            print("-" * 50)

            time.sleep(60)
    except KeyboardInterrupt: print("Watcher Stopped.")
    finally: mt5.shutdown()

if __name__ == "__main__":
    monitor_market()
