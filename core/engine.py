import MetaTrader5 as mt5
import time
import json
import sqlite3
from datetime import datetime
import config
from utils.helpers import (
    calculate_ema, calculate_rsi, fetch_latest_gold_news, fetch_high_impact_news,
    get_mtf_trends, get_filling_mode, get_account_risk, ask_ai, close_positions_by_type,
    is_market_open, get_market_session, get_daily_pnl
)

# ================= KONFIGURASI ENGINE =================
SYMBOL = config.SYMBOL
TIMEFRAME = mt5.TIMEFRAME_M1
LOT_SIZE = config.DEFAULT_LOT
RATING_THRESHOLD = config.RATING_THRESHOLD
STOP_LOSS_PIPS = config.STOP_LOSS_PIPS
TAKE_PROFIT_PIPS = config.TAKE_PROFIT_PIPS
COOLDOWN_SECONDS = config.COOLDOWN_SECONDS
COOLDOWN_AFTER_LOSS = 180
MAX_TRADES = config.MAX_TRADES
MIN_MARGIN_LEVEL = config.MIN_MARGIN_LEVEL
HARD_TP_USD = config.HARD_TP_USD
EMERGENCY_SL_USD = config.EMERGENCY_SL_USD
MAX_CONSEC_LOSSES = config.MAX_CONSEC_LOSSES
DB_FILE = config.DB_FILE

def load_trade_history():
    history = []
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT time, ticket, type, price, result, ai_reason FROM trade_history ORDER BY id ASC")
        rows = cursor.fetchall()
        for r in rows[-15:]:
            history.append({"time": r[0], "ticket": r[1], "type": r[2], "price": r[3], "result": r[4], "ai_reason": r[5]})
        conn.close()
    except Exception as e: print(f"⚠️ DB Error (Load History): {e}")
    return history

def save_to_history(ticket, type_str, price, result_str, reason):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute(
            "INSERT INTO trade_history (time, ticket, type, price, result, ai_reason) VALUES (?, ?, ?, ?, ?, ?)",
            (time_str, ticket, type_str, price, result_str, reason)
        )
        conn.commit(); conn.close()
    except Exception as e: print(f"⚠️ DB Error (Save History): {e}")

def load_long_term_insights():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT insight FROM long_term_insights ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else ""
    except Exception as e: print(f"⚠️ DB Error (Load Insights): {e}")
    return ""

def update_long_term_insights():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT time, type, price, result FROM trade_history ORDER BY id ASC")
        rows = cursor.fetchall()
        closed = [r for r in rows if r[3] not in ["OPENED"]][-30:]
        if len(closed) < 5:
            conn.close(); return
        
        wins = sum(1 for r in closed if r[3] == "CLOSED_BY_HARDCODE")
        losses = sum(1 for r in closed if r[3] == "CLOSED_BY_EMERGENCY_SL")
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0
        summary_text = "\n".join([f"- [{r[0]}] {r[1]} @ {r[2]} → {r[3]}" for r in closed[-20:]])

        insight_prompt = (
            f"Kamu adalah analis trading emas XAUUSD.\n30 trade terakhir:\n{summary_text}\n"
            f"Win rate: {win_rate:.1f}%\nBuat insight singkat (1-3 kalimat) Bahasa Indonesia."
        )
        res = ask_ai(insight_prompt)
        new_insight = res.get("response", "").strip() if res else ""

        if new_insight:
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            cursor.execute(
                "INSERT INTO long_term_insights (date_time, win_rate, total_evaluated, insight) VALUES (?, ?, ?, ?)",
                (date_str, f"{win_rate:.1f}%", total, new_insight)
            )
            conn.commit(); print(f"🧠 LONG-TERM UPDATE: {new_insight[:80]}...")
        conn.close()
    except Exception as e: print(f"⚠️ Gagal update insight DB: {e}")

def manage_trailing_stop():
    """Mengelola Trailing Stop dan Break-Even untuk posisi terbuka"""
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions:
        return

    point = mt5.symbol_info(SYMBOL).point
    for pos in positions:
        current_price = mt5.symbol_info_tick(SYMBOL).bid if pos.type == mt5.POSITION_TYPE_BUY else mt5.symbol_info_tick(SYMBOL).ask
        
        # Hitung Profit dalam Pips
        if pos.type == mt5.POSITION_TYPE_BUY:
            profit_pips = (current_price - pos.price_open) / point
        else:
            profit_pips = (pos.price_open - current_price) / point

        # 1. Logic Break-Even
        if profit_pips >= config.BREAK_EVEN_PIPS:
            # Jika SL belum di atas/di bawah harga open (tergantung tipe)
            new_sl = 0.0
            if pos.type == mt5.POSITION_TYPE_BUY:
                if pos.sl < pos.price_open:
                    new_sl = pos.price_open + (10 * point) # BE + 10 pips buffer
            else:
                if pos.sl > pos.price_open or pos.sl == 0:
                    new_sl = pos.price_open - (10 * point)

            if new_sl > 0:
                print(f"🛡️ BREAK-EVEN: Menggeser SL ke BE (+10) untuk tiket {pos.ticket}")
                request = {
                    "action": mt5.TRADE_ACTION_SLTP, "symbol": SYMBOL, "position": pos.ticket,
                    "sl": new_sl, "tp": pos.tp, "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC,
                }
                mt5.order_send(request)

        # 2. Logic Trailing Stop
        if profit_pips >= config.TRAILING_STOP_PIPS + 100: # Mulai geser setelah profit > TS + buffer
            new_sl = 0.0
            if pos.type == mt5.POSITION_TYPE_BUY:
                potential_sl = current_price - (config.TRAILING_STOP_PIPS * point)
                if potential_sl > pos.sl:
                    new_sl = potential_sl
            else:
                potential_sl = current_price + (config.TRAILING_STOP_PIPS * point)
                if potential_sl < pos.sl or pos.sl == 0:
                    new_sl = potential_sl

            if new_sl > 0:
                print(f"📈 TRAILING: Menggeser SL ke {new_sl} untuk tiket {pos.ticket}")
                request = {
                    "action": mt5.TRADE_ACTION_SLTP, "symbol": SYMBOL, "position": pos.ticket,
                    "sl": new_sl, "tp": pos.tp, "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC,
                }
                mt5.order_send(request)

def run_engine():
    if not mt5.initialize(login=config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER):
        print(f"❌ MT5 Gagal Konek ke {config.MT5_SERVER}.")
        return

    print(f"🚀 [TRADING ENGINE] Mesin Intelijen {SYMBOL} Aktif (Mode: {config.AI_MODE})")
    consecutive_losses = 0
    last_position_count = 0
    completed_trades = 0
    
    # AI Stats Tracking
    total_tokens = 0
    total_requests = 0

    try:
        while True:
            # 1. DAILY DRAWDOWN GUARD
            daily_pnl = get_daily_pnl()
            if daily_pnl <= config.MAX_DAILY_LOSS_USD:
                print(f"🚨 KILL SWITCH AKTIF: Rugi harian ${daily_pnl} mencapai batas ${config.MAX_DAILY_LOSS_USD}. Berhenti hari ini.")
                # Tutup semua posisi jika ada
                close_positions_by_type(SYMBOL, mt5.POSITION_TYPE_BUY)
                close_positions_by_type(SYMBOL, mt5.POSITION_TYPE_SELL)
                time.sleep(3600); continue # Tunggu 1 jam sebelum cek lagi

            if not is_market_open(SYMBOL):
                print(f"💤 PASAR TUTUP: {SYMBOL} sedang tidak aktif. Menunggu 5 menit...")
                time.sleep(300); continue

            rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 50)
            if rates is None or len(rates) < 20:
                print("⏳ Sinkronisasi data..."); time.sleep(5); continue

            prices = [r['close'] for r in rates]
            current_price = prices[-1]
            ema9, ema21, rsi = calculate_ema(prices, 9), calculate_ema(prices, 21), calculate_rsi(prices, 14)
            trend = "UP" if ema9 and ema21 and ema9 > ema21 else "DOWN"
            risk = get_account_risk(MIN_MARGIN_LEVEL)
            if not risk["can_trade"]:
                print(f"⚠️ RISK GUARD: Margin Level {risk['margin_level']}% RENDAH!"); time.sleep(30); continue

            positions = mt5.positions_get(symbol=SYMBOL)
            total_profit = sum(pos.profit for pos in positions) if positions else 0.0
            
            # 2. MANAGE TRAILING STOP
            if positions:
                manage_trailing_stop()
            # Tracking Loss Berturut-turut
            curr_pos_count = len(positions) if positions else 0
            if last_position_count > 0 and curr_pos_count == 0:
                if total_profit < 0: consecutive_losses += 1
                else: consecutive_losses = 0
            last_position_count = curr_pos_count

            if consecutive_losses >= MAX_CONSEC_LOSSES and curr_pos_count == 0:
                print(f"🚨 PAUSE: {consecutive_losses} loss berturut-turut!"); time.sleep(COOLDOWN_AFTER_LOSS * 2)
                consecutive_losses = 0; continue

            # Proteksi Hardcoded
            if total_profit >= HARD_TP_USD or total_profit <= EMERGENCY_SL_USD:
                print(f"💰/🚨 EXIT: Profit/Loss ${total_profit:.2f} treshold hit.")
                close_positions_by_type(SYMBOL, mt5.POSITION_TYPE_BUY)
                close_positions_by_type(SYMBOL, mt5.POSITION_TYPE_SELL)
                mode = "CLOSED_BY_HARDCODE" if total_profit >= HARD_TP_USD else "CLOSED_BY_EMERGENCY_SL"
                save_to_history(0, "ALL", current_price, mode, "Target/Stop hit.")
                completed_trades += 1
                if completed_trades % 10 == 0: update_long_term_insights()
                time.sleep(COOLDOWN_SECONDS); continue

            # RAKIT PROMPT (Optimized for Tokens)
            mtf = get_mtf_trends(SYMBOL)
            session = get_market_session()
            history_text = "\n".join([f"{h['type']}:{h['result']}" for h in load_trade_history()[-15:]])
            news_txt = fetch_latest_gold_news()[:200]
            high_txt = fetch_high_impact_news()[:150]
            
            prompt = (
                f"GOLD_{SYMBOL}_M1 | Session:{session}\n"
                f"P:{current_price} | R:{rsi} | T:{trend} | DailyPnL:${daily_pnl}\n"
                f"M15:{mtf.get('M15')} | H1:{mtf.get('H1')}\n"
                f"News:{news_txt}\n{high_txt}\n"
                f"Hist:{history_text}\n"
                f"Ref:{load_long_term_insights()[:200]}\n"
                f"Output JSON: decision(BUY/SELL/HOLD/CLOSE), confidence(0-1), reason, sl_pips"
            )

            print(f"🧠 Meminta Analisa AI ({config.AI_MODE})...", end="", flush=True)
            res_ai = ask_ai(prompt)
            if not res_ai: print("❌ Gagal AI."); time.sleep(10); continue
            
            # Update Stats
            total_requests += 1
            usage = res_ai.get("usage", {})
            last_tokens = usage.get("totalTokenCount", 0)
            total_tokens += last_tokens
            
            # Sisa Request (Estimasi RPD 1500)
            remaining_rpd = max(0, 1500 - total_requests)
            stats_msg = f" [Req:{total_requests} (Sisa:~{remaining_rpd}) | Tokens:{total_tokens}]"

            try:
                resp = json.loads(res_ai.get('response', '{}'))
                decision = resp.get("decision", "HOLD").upper()
                confidence = resp.get("confidence", 0.0)
                reason = resp.get("reason", "No reason")
                print(f" ✅ AI: {decision} ({confidence}){stats_msg}")

                if decision == "CLOSE":
                    if not (total_profit < 0 and total_profit > EMERGENCY_SL_USD):
                        close_positions_by_type(SYMBOL, mt5.POSITION_TYPE_BUY)
                        close_positions_by_type(SYMBOL, mt5.POSITION_TYPE_SELL)
                        save_to_history(0, "ALL", current_price, "CLOSED_BY_AI", reason)

                elif decision in ["BUY", "SELL"] and confidence >= RATING_THRESHOLD:
                    hard_blocked = (decision == "BUY" and rsi >= 85) or (decision == "SELL" and rsi <= 15)
                    if not hard_blocked and curr_pos_count < MAX_TRADES:
                        # Tutup Lawan
                        opposing = mt5.POSITION_TYPE_SELL if decision == "BUY" else mt5.POSITION_TYPE_BUY
                        close_positions_by_type(SYMBOL, opposing)
                        
                        price = mt5.symbol_info_tick(SYMBOL).ask if decision == "BUY" else mt5.symbol_info_tick(SYMBOL).bid
                        point = mt5.symbol_info(SYMBOL).point
                        ai_sl = max(300, min(int(resp.get("sl_pips", STOP_LOSS_PIPS)), 3000))
                        sl = price - ai_sl * point if decision == "BUY" else price + ai_sl * point
                        tp = price + ai_sl * point if decision == "BUY" else price - ai_sl * point
                        
                        req = {
                            "action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": LOT_SIZE,
                            "type": mt5.ORDER_TYPE_BUY if decision == "BUY" else mt5.ORDER_TYPE_SELL,
                            "price": price, "sl": sl, "tp": tp, "deviation": 20,
                            "magic": config.MAGIC_NUMBER, "comment": "AI Hybrid V2",
                            "type_filling": get_filling_mode(SYMBOL),
                        }
                        result = mt5.order_send(req)
                        if result.retcode == mt5.TRADE_RETCODE_DONE:
                            save_to_history(result.order, decision, price, "OPENED", reason)
                            consecutive_losses = 0
            except Exception as e: print(f"❌ Parse Error: {e}")
            time.sleep(COOLDOWN_SECONDS)

    except KeyboardInterrupt: print("Shutdown.")
    finally: mt5.shutdown()

if __name__ == "__main__":
    run_engine()
