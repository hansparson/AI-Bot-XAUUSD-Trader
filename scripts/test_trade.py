import MetaTrader5 as mt5
import os
import sys

# Tambahkan project root ke sys.path untuk impor config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def test_single_trade():
    print("=== MT5 TRADE EXECUTION TEST ===")
    
    # 1. Inisialisasi
    if not mt5.initialize():
        print(f"❌ Inisialisasi MT5 Gagal: {mt5.last_error()}")
        return

    # 2. Login (Gunakan Demo sesuai .env)
    print(f"🔑 Mencoba Login ke {config.MT5_SERVER} (ID: {config.MT5_LOGIN})...")
    authorized = mt5.login(config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER)
    
    if not authorized:
        print(f"❌ Login Gagal: {mt5.last_error()}")
        mt5.shutdown()
        return

    symbol = config.SYMBOL
    lot = 0.01 # Minimal lot untuk keamanan test
    
    # 3. Persiapan Order BUY
    print(f"📦 Menyiapkan Order BUY 0.01 {symbol}...")
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"❌ Gagal mengambil harga untuk {symbol}")
        mt5.shutdown()
        return

    price = tick.ask
    sl = price - (500 * mt5.symbol_info(symbol).point) # 500 pips SL
    tp = price + (500 * mt5.symbol_info(symbol).point) # 500 pips TP

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 999999, # Magic khusus testing
        "comment": "OPENCLAW TEST RUN",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    # 4. Kirim Order
    print("🚀 Mengirim Order ke Broker...")
    result = mt5.order_send(request)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Order GAGAL! Kode error: {result.retcode}")
        print(f"Saran: Cek apakah pasar sudah buka atau limit margin cukup.")
    else:
        print(f"✅ Order BERHASIL!")
        print(f"Ticket: {result.order}")
        print(f"Harga: {result.price}")
        print(f"Silakan cek terminal MetaTrader 5 Anda.")

    mt5.shutdown()

if __name__ == "__main__":
    test_single_trade()
