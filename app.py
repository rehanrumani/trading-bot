from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is live"

@app.route("/tv_signal", methods=["POST"])
def tradingview_signal():
    data = request.json
    # Example: {"signal": "BUY", "pair": "BTC/USDT"}
    print("Received signal:", data)

    # In real bot, you'd call 3Commas or Binance API here
    return jsonify({"status": "received", "data": data}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
