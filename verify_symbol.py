import MetaTrader5 as mt5
import config

def check_symbol():
    if not mt5.initialize(login=config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER):
        print("Gagal MT5")
        return

    symbol = config.SYMBOL
    info = mt5.symbol_info(symbol)
    if info is None:
        print(f"Symbol {symbol} tidak ditemukan!")
        mt5.shutdown()
        return

    tick = mt5.symbol_info_tick(symbol)
    print(f"--- SYMBOL INFO: {symbol} ---")
    print(f"Bid: {tick.bid if tick else 'N/A'}")
    print(f"Ask: {tick.ask if tick else 'N/A'}")
    print(f"Digits: {info.digits}")
    print(f"Trade Mode: {info.trade_mode}")
    print(f"Price Change: {info.price_change if hasattr(info, 'price_change') else 'N/A'}")
    
    # Cek Harga XAUUSD (Standard) jika ada
    info_std = mt5.symbol_info("XAUUSD")
    if info_std:
        tick_std = mt5.symbol_info_tick("XAUUSD")
        print(f"\n--- COMPARISON (XAUUSD Standard) ---")
        print(f"Bid: {tick_std.bid if tick_std else 'N/A'}")
    
    mt5.shutdown()

if __name__ == "__main__":
    check_symbol()
