#!/usr/bin/env python3
"""
VNStock API Service - Using vnstock 3.x
Provides HTTP endpoints to fetch Vietnamese stock prices using vnstock library
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
import os

try:
    from vnstock import Vnstock
except ImportError:
    print("WARNING: vnstock not installed. Install with: pip install vnstock")
    Vnstock = None

app = Flask(__name__)
CORS(app)

API_KEY = os.getenv('API_KEY', None)

def verify_api_key():
    if API_KEY:
        provided_key = request.headers.get('X-API-Key')
        if provided_key != API_KEY:
            return False
    return True

def get_stock_price(symbol):
    try:
        if Vnstock is None:
            return {"error": "vnstock not installed", "symbol": symbol.upper()}

        # Try multiple sources in case one is blocked by PythonAnywhere
        sources = ['TCBS', 'VND', 'MSN', 'VCI']
        last_error = None

        for source in sources:
            try:
                stock = Vnstock().stock(symbol=symbol.upper(), source=source)
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')

                df = stock.quote.history(start=start_date, end=end_date, interval='1D')

                if df is not None and not df.empty:
                    # Success! Break out of loop
                    break
            except Exception as e:
                last_error = str(e)
                continue

        # If we got here and df is None, all sources failed
        if 'df' not in locals() or df is None or df.empty:
            return {"error": f"No data available for {symbol}. Last error: {last_error}", "symbol": symbol.upper()}

        latest = df.iloc[-1]
        price = float(latest['close'])

        return {
            "symbol": symbol.upper(),
            "price": price,
            "date": str(latest['time']) if 'time' in latest else end_date,
            "source": "vnstock3-api",
            "open": float(latest['open']) if 'open' in latest else None,
            "high": float(latest['high']) if 'high' in latest else None,
            "low": float(latest['low']) if 'low' in latest else None,
            "volume": int(latest['volume']) if 'volume' in latest else None
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol.upper()}

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "service": "vnstock-api",
        "version": "2.0.0-vnstock3"
    })

@app.route('/api/stock/<symbol>', methods=['GET'])
def get_stock(symbol):
    if not verify_api_key():
        return jsonify({"error": "Unauthorized"}), 401

    result = get_stock_price(symbol)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)

@app.route('/api/stocks', methods=['POST'])
def get_stocks_batch():
    if not verify_api_key():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    symbols = data.get('symbols', [])

    if not symbols or not isinstance(symbols, list):
        return jsonify({"error": "symbols must be a non-empty array"}), 400

    results = []
    for symbol in symbols:
        result = get_stock_price(symbol)
        results.append(result)

    return jsonify({"results": results, "count": len(results)})

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "service": "VNStock API",
        "version": "2.0.0-vnstock3",
        "endpoints": {
            "health": "GET /health",
            "single_stock": "GET /api/stock/:symbol",
            "batch_stocks": "POST /api/stocks (body: {symbols: []})"
        }
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
