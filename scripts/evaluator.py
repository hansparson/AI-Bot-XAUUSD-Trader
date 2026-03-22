import MetaTrader5 as mt5
import sqlite3
import os
import sys
import json
from datetime import datetime, timedelta

# Tambahkan project root ke sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.helpers import ask_ai

def evaluate_performance():
    print("=== AI PERFORMANCE EVALUATOR ===")
    
    # 1. Inisialisasi
    if not mt5.initialize(login=config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER):
        print("❌ MT5 Gagal!")
        return

    # 2. Ambil Riwayat dari DB
    conn = sqlite3.connect(config.DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT ticket, type, ai_reason FROM trade_history ORDER BY id DESC LIMIT 50")
    db_trades = cursor.fetchall()

    if not db_trades:
        print("ℹ️ Belum ada riwayat transaksi di database.")
        conn.close(); mt5.shutdown(); return

    # 3. Sinkronkan dengan Profit di MT5
    performance_summary = []
    total_profit = 0
    wins = 0

    for ticket, trade_type, reason in db_trades:
        # Cari deal di MT5 history
        history_deals = mt5.history_deals_get(ticket=ticket)
        if history_deals:
            deal = history_deals[0]
            # Kita cari deal OUT yang menutup posisi ini
            # Atau jika posisi masih OPEN, kita skip untuk evaluasi
            pass
            
        # Untuk simplifikasi saat ini, kita ambil deals 24 jam terakhir
        pass

    # Ambil deals 24 jam terakhir
    from_date = datetime.now() - timedelta(hours=24)
    to_date = datetime.now()
    history_deals = mt5.history_deals_get(from_date, to_date)
    
    analysis_input = ""
    if history_deals:
        for deal in history_deals:
            if deal.entry == mt5.DEAL_ENTRY_OUT:
                pnl = deal.profit + deal.commission + deal.swap
                win_status = "WIN" if pnl > 0 else "LOSS"
                analysis_input += f"Ticket {deal.position_id}: {win_status} (${pnl:.2f})\n"
                total_profit += pnl
                if pnl > 0: wins += 1

    if not analysis_input:
        print("ℹ️ Tidak ada transaksi untuk dievaluasi dalam 24 jam terakhir.")
        conn.close(); mt5.shutdown(); return

    print(f"📊 Mengevaluasi {len(history_deals)} deals... Total PnL: ${total_profit:.2f}")

    # 4. Mintalah AI untuk Belajar
    prompt = (
        f"Sebagai Senior Trading Quantitative Analyst, evaluasi hasil trading berikut:\n"
        f"{analysis_input}\n"
        f"Berdasarkan hasil ini, berikan 1 insight strategis (maks 150 karakter) "
        f"untuk meningkatkan akurasi sistem di masa depan. Fokus pada pola yang berhasil."
    )
    
    print("🧠 AI sedang merangkum pelajaran hari ini...")
    res = ask_ai(prompt)
    if res:
        insight_text = res.get('response', 'Konsisten dengan strategi EMA.').strip()
        # Bersihkan insight
        insight_text = insight_text.replace("\n", " ")[:200]
        
        # Simpan ke DB
        win_rate = f"{(wins/len(history_deals)*100):.1f}%" if history_deals else "0%"
        cursor.execute(
            "INSERT INTO long_term_insights (date_time, win_rate, total_evaluated, insight) VALUES (?, ?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M"), win_rate, len(history_deals), insight_text)
        )
        conn.commit()
        
        # Update File Teks untuk Engine
        insight_file = os.path.join("data", "trading_insights.txt")
        with open(insight_file, "w") as f:
            f.write(insight_text)
            
        print(f"✅ Pelajaran Berhasil Disimpan: \"{insight_text}\"")
    
    conn.close()
    mt5.shutdown()

if __name__ == "__main__":
    evaluate_performance()
