import MetaTrader5 as mt5
import json
import sqlite3
import config
from utils.helpers import ask_ai
from datetime import datetime, timedelta

def run_evaluator():
    if not mt5.initialize(login=config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER):
        print(f"Gagal konek ke {config.MT5_SERVER}!")
        return
        
    sekarang = datetime.now()
    kemarin = sekarang - timedelta(days=1)
    deals = mt5.history_deals_get(kemarin, sekarang)
    
    if deals is None or len(deals) == 0:
        print("Belum ada transaksi hari ini untuk dievaluasi.")
        mt5.shutdown(); return
        
    jumlah_transaksi = 0
    profit_total = 0.0
    ringkasan = f"=== HASIL TRADING HARI INI ({sekarang.strftime('%Y-%m-%d')}) ===\n"
    
    for deal in deals:
        if deal.entry == mt5.DEAL_ENTRY_IN: continue
        profit = deal.profit
        if profit == 0.0 and deal.fee == 0.0: continue
        jumlah_transaksi += 1
        profit_total += profit
        ringkasan += f"- {deal.symbol} | Profit: ${profit:.2f}\n"
    
    ringkasan += f"---------------------------------\nTotal Profit/Rugi: ${profit_total:.2f} (transaksi: {jumlah_transaksi})"
    print(ringkasan)

    print(f"🧠 Meminta Analisa AI Evaluator ({config.AI_MODE})...")
    context_eval = f"TRADING_LOG:\n{ringkasan}\nTask: Berikan 1 insight 'Subconscious' (2 kalimat max) Bahasa Indonesia untuk koreksi strategi."
    
    res = ask_ai(context_eval)
    ai_insight = res.get("response", "Error AI") if res else "Error"
    
    try:
        conn = sqlite3.connect(config.DB_FILE)
        cursor = conn.cursor()
        date_str = sekarang.strftime('%Y-%m-%d %H:%M')
        cursor.execute(
            "INSERT INTO long_term_insights (date_time, win_rate, total_evaluated, insight) VALUES (?, ?, ?, ?)",
            (date_str, "Daily Gen", jumlah_transaksi, ai_insight)
        )
        conn.commit(); conn.close()
        print(f"✅ Evaluasi Selesai! Insight disimpan.")
    except Exception as e: print(f"❌ Gagal update memori: {e}")
    mt5.shutdown()

if __name__ == "__main__":
    run_evaluator()
