import sys
import json
import MetaTrader5 as mt5
import config

def run_manual_tool():
    if not mt5.initialize(login=config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER):
        print(json.dumps({"error": "Failed to connect to MT5"}))
        return

    command = sys.argv[1] if len(sys.argv) > 1 else "status"

    try:
        if command == "status":
            terminal_info = mt5.terminal_info()
            account_info = mt5.account_info()
            if terminal_info is None or account_info is None:
                print(json.dumps({"error": "Failed to retrieve terminal/account info"}))
            else:
                print(json.dumps({
                    "status": "Connected",
                    "login": account_info.login,
                    "broker": account_info.company,
                    "terminal_build": terminal_info.build
                }))
                
        elif command == "price":
            symbol = sys.argv[2] if len(sys.argv) > 2 else config.SYMBOL
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                print(json.dumps({
                    "symbol": symbol,
                    "bid": tick.bid,
                    "ask": tick.ask,
                    "last": tick.last
                }))
            else:
                print(json.dumps({"error": "Failed to get price"}))

        elif command == "close_all":
            symbol = config.SYMBOL
            positions = mt5.positions_get(symbol=symbol)
            if positions is None or len(positions) == 0:
                print(json.dumps({"status": "No open positions"}))
            else:
                for pos in positions:
                    tick = mt5.symbol_info_tick(symbol)
                    order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
                    price = tick.bid if pos.type == mt5.POSITION_TYPE_BUY else tick.ask
                    
                    request = {
                        "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": pos.volume,
                        "type": order_type, "position": pos.ticket, "price": price,
                        "deviation": 20, "magic": config.MAGIC_NUMBER, "comment": "Manual Close All",
                        "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_IOC,
                    }
                    mt5.order_send(request)
                print(json.dumps({"status": f"Closed {len(positions)} positions"}))
                
        else:
            print(json.dumps({"error": f"Unknown command: {command}"}))

    except Exception as e:
        print(json.dumps({"error": str(e)}))
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python manual_tool.py [status|price|close_all]")
    else:
        run_manual_tool()
