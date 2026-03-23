import MetaTrader5 as mt5
import time
import json
import sqlite3
from datetime import datetime
import config
from utils.helpers import (
    calculate_ema, calculate_rsi, calculate_atr, get_market_regime,
    fetch_latest_gold_news, fetch_high_impact_news, is_high_impact_news_active,
    get_mtf_trends, get_filling_mode, get_account_risk, ask_ai, close_positions_by_type,
    is_market_open, get_market_session, get_daily_pnl, get_spread, is_valid_rejection,
    get_equity_drawdown, is_equity_curve_healthy, can_resume_trading
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

# PRO Features
PRO_MODE = config.PRO_MODE
ATR_SL_MULT = config.ATR_SL_MULT
ATR_TP_MULT = config.ATR_TP_MULT
ATR_BE_MULT = config.ATR_BE_MULT
ATR_TRAIL_MULT = config.ATR_TRAIL_MULT
USE_SESSION_FILTER_PRO = config.USE_SESSION_FILTER_PRO
USE_NEWS_FILTER_PRO = config.USE_NEWS_FILTER_PRO
DYNAMIC_AI_THRESHOLD = config.DYNAMIC_AI_THRESHOLD

# Institutional / Risk Manager Features
MAX_SPREAD_POINTS = config.MAX_SPREAD_POINTS
MAX_DAILY_TRADES = config.MAX_DAILY_TRADES
ENSEMBLE_AI = config.ENSEMBLE_AI
WEIGHT_TECH = config.WEIGHT_TECH
WEIGHT_OLLAMA = config.WEIGHT_OLLAMA
WEIGHT_GEMINI = config.WEIGHT_GEMINI
EQUITY_DD_THRESHOLD = config.EQUITY_DD_THRESHOLD
TRADE_COOLDOWN = config.TRADE_COOLDOWN

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

def save_to_history(ticket, type_str, price, result_str, reason, regime=None, session=None, atr=None, entry_type=None):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute(
            "INSERT INTO trade_history (time, ticket, type, price, result, ai_reason, regime, session, atr, entry_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (time_str, ticket, type_str, price, result_str, reason, regime, session, atr, entry_type)
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
    
    # Hitung ATR untuk PRO Mode
    atr = None
    if PRO_MODE:
        rates_m1 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 30)
        if rates_m1 is not None:
            atr = calculate_atr(rates_m1, 14)

    for pos in positions:
        tick = mt5.symbol_info_tick(SYMBOL)
        current_price = tick.bid if pos.type == mt5.POSITION_TYPE_BUY else tick.ask
        
        # Jarak Target (Pips)
        if PRO_MODE and atr:
            be_pips = (atr * ATR_BE_MULT) / point
            trail_pips = (atr * ATR_TRAIL_MULT) / point
        else:
            be_pips = config.BREAK_EVEN_PIPS
            trail_pips = config.TRAILING_STOP_PIPS

        # Hitung Profit dalam Pips
        if pos.type == mt5.POSITION_TYPE_BUY:
            profit_pips = (current_price - pos.price_open) / point
        else:
            profit_pips = (pos.price_open - current_price) / point

        # 1. Logic Break-Even
        if profit_pips >= be_pips:
            new_sl = 0.0
            if pos.type == mt5.POSITION_TYPE_BUY:
                if pos.sl < pos.price_open:
                    new_sl = pos.price_open + (15 * point) # BE + 15 pips
            else:
                if pos.sl > pos.price_open or pos.sl == 0:
                    new_sl = pos.price_open - (15 * point)

            if new_sl > 0:
                print(f"🛡️ PRO BE: Menggeser SL ke BE (+15) untuk tiket {pos.ticket}")
                request = {
                    "action": mt5.TRADE_ACTION_SLTP, "symbol": SYMBOL, "position": pos.ticket,
                    "sl": new_sl, "tp": pos.tp, "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC,
                }
                mt5.order_send(request)

        # 2. Logic Trailing Stop
        if profit_pips >= trail_pips + 150: # Buffer 150 pips
            new_sl = 0.0
            if pos.type == mt5.POSITION_TYPE_BUY:
                potential_sl = current_price - (trail_pips * point)
                if potential_sl > pos.sl:
                    new_sl = potential_sl
            else:
                potential_sl = current_price + (trail_pips * point)
                if potential_sl < pos.sl or pos.sl == 0:
                    new_sl = potential_sl

            if new_sl > 0:
                print(f"📈 PRO TRAILING: Menggeser SL ke {new_sl} untuk {pos.ticket}")
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
    trades_today = 0
    completed_trades = 0
    last_trade_time = datetime.min
    
    # State untuk Institutional Pullback
    pending_signal = "HOLD"
    pullback_ready = False
    
    # Heartbeat counter
    loop_count = 0
    
    try:
        while True:
            # 0. HEARTBEAT (Status monitoring)
            loop_count += 1
            
            # Diagnostic Awal (Immediate)
            if loop_count == 1 or loop_count % 10 == 0:
                acc = mt5.account_info()
                print(f"🔍 Monitoring [{SYMBOL}]: Price:{mt5.symbol_info_tick(SYMBOL).bid if mt5.symbol_info_tick(SYMBOL) else 0} | Equity:${acc.equity if acc else 0}")

            if loop_count >= 60: # Sinyal status setiap ~10 menit (60 * 10s)
                print(f"💓 HEARTBEAT | Pnl: ${daily_pnl} | Regime: {regime} | Pos: {curr_pos_count} | Spr: {get_spread(SYMBOL)}")
                loop_count = 0

            # 1. INSTITUTIONAL SAFETY GUARDS
            # A. Drawdown & Daily PnL
            daily_pnl = get_daily_pnl()
            if daily_pnl <= config.MAX_DAILY_LOSS_USD:
                if config.ACCOUNT_MODE == "DEMO":
                    if loop_count % 12 == 0:
                        print(f"⚠️ RISK: Daily Loss Limit Hit (${daily_pnl}), but continuing because of DEMO MODE.")
                else:
                    print(f"🚨 KILL SWITCH: Daily Loss Limit Hit (${daily_pnl}). Pausing...")
                    close_positions_by_type(SYMBOL, mt5.POSITION_TYPE_BUY)
                    close_positions_by_type(SYMBOL, mt5.POSITION_TYPE_SELL)
                    time.sleep(3600); continue

            # B. Equity Curve Health (3-day sequential loss)
            if not is_equity_curve_healthy():
                print(f"📉 EQUITY GUARD: sequential losing days detected. Safety Pause...")
                if not can_resume_trading():
                    time.sleep(3600); continue
                print("🧘 SMART RESUME: Market conditions stabilized. Resuming...")

            # C. Market Open
            if not is_market_open(SYMBOL):
                print(f"💤 PASAR TUTUP: {SYMBOL} sedang tidak aktif. Menunggu 5 menit...")
                time.sleep(300); continue

            # 2. PRO FILTERS (Session & News)
            if PRO_MODE:
                session = get_market_session()
                is_prime_time = "LONDON" in session or "NEW YORK" in session
                if USE_SESSION_FILTER_PRO and not is_prime_time:
                    print(f"😴 LOW VOLATILITY: Sesi {session}. Menunggu London/NY (UTC 08:00-21:00)...")
                    time.sleep(60); continue
                
                if USE_NEWS_FILTER_PRO and is_high_impact_news_active():
                    print("⚠️ NEWS GUARD: Berita High Impact terdeteksi. Menunggu 5 menit...")
                    time.sleep(300); continue

            # 3. TECHNICAL INDICATORS
            rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 100)
            if rates is None or len(rates) < 50:
                print("⏳ Sinkronisasi data..."); time.sleep(5); continue

            prices = [r['close'] for r in rates]
            current_price = prices[-1]
            ema20 = calculate_ema(prices, 20)
            ema50 = calculate_ema(prices, 50)
            ema200 = calculate_ema(prices, 200)
            rsi = calculate_rsi(prices, 14)
            atr = calculate_atr(rates, 14)
            regime = get_market_regime(prices)
            
            risk = get_account_risk(MIN_MARGIN_LEVEL)
            if not risk["can_trade"]:
                print(f"⚠️ RISK GUARD: Margin Level {risk['margin_level']}% RENDAH!"); time.sleep(30); continue

            positions = mt5.positions_get(symbol=SYMBOL)
            total_profit = sum(pos.profit for pos in positions) if positions else 0.0
            curr_pos_count = len(positions) if positions else 0
            
            # 4. MANAGE OPEN POSITIONS
            if positions:
                manage_trailing_stop()
                # Proteksi Hardcoded (TP/SL USD)
                if total_profit >= HARD_TP_USD or total_profit <= EMERGENCY_SL_USD:
                    print(f"💰/🚨 EXIT: Profit/Loss ${total_profit:.2f} threshold hit.")
                    close_positions_by_type(SYMBOL, mt5.POSITION_TYPE_BUY)
                    close_positions_by_type(SYMBOL, mt5.POSITION_TYPE_SELL)
                    save_to_history(0, "ALL", current_price, "EXIT_HARDCODE", f"PnL: ${total_profit}", regime, session, atr, "HARD_EXIT")
                    completed_trades += 1
                    if completed_trades % 5 == 0: update_long_term_insights()
                    time.sleep(COOLDOWN_SECONDS); continue

            # 5. INSTITUTIONAL SIGNAL TRIGGER
            # A. Detect Crossover (The Trigger)
            if ema20 and ema50:
                new_signal = "HOLD"
                technical_score = 0.5
                
                if ema20 > ema50 and rsi < 80:
                    new_signal = "BUY"
                    # Soft Filter EMA200
                    if not PRO_MODE or (ema200 and current_price > ema200):
                        technical_score = 0.9
                    else:
                        technical_score = 0.6 # Aggressive: allow even below EMA200 with penalty
                elif ema20 < ema50 and rsi > 20:
                    new_signal = "SELL"
                    # Soft Filter EMA200
                    if not PRO_MODE or (ema200 and current_price < ema200):
                        technical_score = 0.9
                    else:
                        technical_score = 0.6 # Aggressive
                
                if new_signal == "HOLD" and loop_count % 12 == 0:
                    print(f"👀 MONITORING: Price:{current_price:.2f} | EMA20:{ema20:.2f} | EMA50:{ema50:.2f} | Trend:{'UP' if ema20 > ema50 else 'DOWN'}")
                
                # State Machine for Pullback
                if new_signal != "HOLD" and pending_signal == "HOLD":
                    print(f"📡 TRIGGER: {new_signal} detected. Waiting for pullback (Proximity)...")
                    pending_signal = new_signal
                    pullback_ready = False
                elif new_signal == "HOLD" and pending_signal != "HOLD":
                    if loop_count % 6 == 0:
                        print(f"⏳ PENDING: {pending_signal} setup still active. Monitoring pullback/rejection...")

            # B. Check for Pullback (Proximity EMA)
            if pending_signal != "HOLD" and not pullback_ready:
                atr = calculate_atr(rates, 14) or 0.5
                # Proximity: Harga masuk dalam range ATR dari EMA (Looser than touch)
                proximity = atr * 0.7
                
                last_candle = rates[-1]
                if pending_signal == "BUY" and last_candle['low'] <= (ema20 + proximity):
                    pullback_ready = True
                    print(f"🔄 PROXIMITY: Price entered EMA20 zone. Confirming...")
                elif pending_signal == "SELL" and last_candle['high'] >= (ema20 - proximity):
                    pullback_ready = True
                    print(f"🔄 PROXIMITY: Price entered EMA20 zone. Confirming...")

            # 6. EXECUTION GUARDS (Institutional)
            can_execute = False
            entry_type = "PULLBACK"
            
            if pending_signal != "HOLD" and pullback_ready:
                atr = calculate_atr(rates, 14) or 0.5
                dist = abs(current_price - ema20)
                
                # Check for Rejection Candle
                if is_valid_rejection(rates, pending_signal):
                    can_execute = True
                else:
                    # Dynamic Entry: Harga mulai menjauh dari EMA
                    if dist > (atr * 0.8): 
                        can_execute = True
                        entry_type = "DYNAMIC_ENTER"
                    elif loop_count % 3 == 0:
                        print(f"🔍 WAITING: Setup {pending_signal} ready | Dist:{dist:.2f} | ATR_Req:{atr*0.8:.2f}")

            # Check Discipline Guards
            if can_execute:
                # 1. Spread Filter
                if get_spread(SYMBOL) > MAX_SPREAD_POINTS:
                    print(f"⚠️ SPREAD GAURD: Spread {get_spread(SYMBOL)} too high."); can_execute = False
                
                # 2. Frequency Filter
                if trades_today >= MAX_DAILY_TRADES:
                    print(f"⚠️ FREQUENCY GUARD: Max daily trades ({MAX_DAILY_TRADES}) reached."); can_execute = False
                
                # 3. Cooldown Filter
                if (datetime.now() - last_trade_time).total_seconds() < TRADE_COOLDOWN:
                    print("⏳ COOLDOWN: Institutional delay between trades."); can_execute = False

            # 7. ENSEMBLE AI VALIDATION
            if can_execute and curr_pos_count < MAX_TRADES:
                mtf = get_mtf_trends(SYMBOL)
                history_text = "\n".join([f"{h['type']}:{h['result']}" for h in load_trade_history()[-10:]])
                news_txt = fetch_latest_gold_news()[:150]
                
                prompt = (
                    f"PRO_FILTER_XAUUSD | Signal:{pending_signal} | Type:{entry_type}\n"
                    f"P:{current_price} | RSI:{rsi:.1f} | ATR:{atr:.2f} | Regime:{regime}\n"
                    f"M15:{mtf.get('M15')} | H1:{mtf.get('H1')}\n"
                    f"JSON: score(0-1), reason"
                )

                # Weighted Scoring (Ensemble or Local)
                score_ollama = 0.5
                score_gemini = 0.5
                final_score = 0.0
                
                # Selalu panggil Ollama (Local)
                res_ollama = ask_ai(prompt, mode_override="LOCAL")
                if res_ollama:
                    try: score_ollama = json.loads(res_ollama.get('response', '{}')).get('score', 0.5)
                    except: pass
                
                if ENSEMBLE_AI:
                    print(f"🧠 ENSEMBLE AI Validating {pending_signal}...", end="", flush=True)
                    res_gemini = ask_ai(prompt, mode_override="CLOUD")
                    if res_gemini:
                        try: score_gemini = json.loads(res_gemini.get('response', '{}')).get('score', 0.5)
                        except: pass
                    else:
                        print(" (Gemini Error! Fallback to local-heavy) ", end="")
                        score_gemini = 0.5
                    
                    if not res_gemini:
                        final_score = (technical_score * 0.6) + (score_ollama * 0.4)
                    else:
                        final_score = (technical_score * WEIGHT_TECH) + (score_ollama * WEIGHT_OLLAMA) + (score_gemini * WEIGHT_GEMINI)
                else:
                    # PURE LOCAL MODE (50% Tech, 50% Ollama)
                    print(f"🧠 LOCAL AI Validating {pending_signal}...", end="", flush=True)
                    final_score = (technical_score * 0.5) + (score_ollama * 0.5)
                
                print(f" [Tech:{technical_score:.1f} | O:{score_ollama:.1f}] -> Final: {final_score:.2f}")

                # MEGA-LOOSE: Jika skor AI tinggi, kita anggap konfirmasi terpenuhi
                if final_score >= RATING_THRESHOLD:
                    can_execute = True # Pastikan bisa lanjut eksekusi
                    # 8. ADAPTIVE POSITION SIZING
                    dd = get_equity_drawdown()
                    risk_mult = 1.0
                    if dd > 10.0: risk_mult = 0.5
                    elif dd > 5.0: risk_mult = 0.75
                    
                    final_lot = round(LOT_SIZE * risk_mult, 2)
                    
                    # EXECUTE
                    price = mt5.symbol_info_tick(SYMBOL).ask if pending_signal == "BUY" else mt5.symbol_info_tick(SYMBOL).bid
                    sl_dist = atr * ATR_SL_MULT
                    tp_dist = atr * ATR_TP_MULT
                    sl = price - sl_dist if pending_signal == "BUY" else price + sl_dist
                    tp = price + tp_dist if pending_signal == "BUY" else price - tp_dist
                    
                    req = {
                        "action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL, "volume": final_lot,
                        "type": mt5.ORDER_TYPE_BUY if pending_signal == "BUY" else mt5.ORDER_TYPE_SELL,
                        "price": price, "sl": sl, "tp": tp, "deviation": 20,
                        "magic": config.MAGIC_NUMBER, "comment": f"INS {entry_type}",
                        "type_filling": get_filling_mode(SYMBOL),
                    }
                    result = mt5.order_send(req)
                    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                        print(f"💰 INSTITUTIONAL TRADE: {pending_signal} {final_lot} @{price:.2f} [Score:{final_score:.2f}]")
                        save_to_history(result.order, pending_signal, price, "OPENED", f"Score:{final_score:.2f}", regime, session, atr, entry_type)
                        last_trade_time = datetime.now()
                        trades_today += 1
                        pending_signal = "HOLD" # Reset state
                    else:
                        print(f"❌ Order Gagal: {result.comment if result else 'Unknown'}")
                else:
                    print(f" ⏭️ SKIPPED: Low Composite Score ({final_score:.2f})")
            
            time.sleep(10)

    except KeyboardInterrupt: print("Shutdown.")
    finally: mt5.shutdown()

if __name__ == "__main__":
    run_engine()
