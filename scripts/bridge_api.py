from flask import Flask, jsonify, request
import MetaTrader5 as mt5
import config
import os

app = Flask(__name__)

# Memastikan MT5 menyala
if not mt5.initialize(login=config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER):
    print("❌ MT5 Initialization failed")

@app.route('/status', methods=['GET'])
def get_status():
    account_info = mt5.account_info()
    if account_info:
        return jsonify({
            "login": account_info.login,
            "equity": account_info.equity,
            "margin_level": account_info.margin_level,
            "broker": account_info.company
        })
    return jsonify({"error": "Failed to get account info"}), 500

@app.route('/price/<symbol>', methods=['GET'])
def get_price(symbol):
    tick = mt5.symbol_info_tick(symbol)
    if tick:
        return jsonify({
            "bid": tick.bid,
            "ask": tick.ask
        })
    return jsonify({"error": "Symbol not found"}), 404

if __name__ == '__main__':
    # Hapus lock file openclaw jika ada (legacy cleanup)
    lock_file = os.path.expanduser("~/.openclaw/agent.lock")
    if os.path.exists(lock_file):
        try: os.remove(lock_file)
        except: pass
        
    app.run(host='0.0.0.0', port=5000)
