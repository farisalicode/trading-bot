import logging
import os
import time
from datetime import datetime
from typing import Any, Dict

from dotenv import load_dotenv
from flask import Flask, jsonify, request

from app.exchange.binance_client import BinanceTestnetClient
from app.storage import append_trade_to_csv
from app.metrics import calculate_metrics, get_trade_summary


load_dotenv()

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/trading_bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("trading_bot_flask")

app = Flask(__name__)

# Track webhook statistics
webhook_stats = {
    "total_requests": 0,
    "successful_trades": 0,
    "failed_trades": 0,
    "invalid_auth": 0,
    "invalid_signal": 0,
    "start_time": datetime.now().isoformat(),
}


def get_config() -> Dict[str, Any]:
    return {
        "alert_auth_token": os.getenv("ALERT_AUTH_TOKEN", ""),
        "symbol": os.getenv("TRADING_SYMBOL", "BTCUSDT"),
        "quantity": float(os.getenv("TRADE_QUANTITY", "0.001")),
        "log_file": os.getenv("LOG_FILE", "logs/trades.csv"),
    }


config = get_config()


@app.get("/")
def health() -> Any:
    """Health check endpoint with basic stats."""
    uptime_seconds = (datetime.now() - datetime.fromisoformat(webhook_stats["start_time"])).total_seconds()
    return jsonify({
        "status": "ok",
        "message": "Flask trading bot webhook is running.",
        "uptime_seconds": int(uptime_seconds),
        "stats": {
            "total_requests": webhook_stats["total_requests"],
            "successful_trades": webhook_stats["successful_trades"],
            "failed_trades": webhook_stats["failed_trades"],
        },
    })


@app.get("/metrics")
def metrics() -> Any:
    """Get detailed trading metrics and statistics."""
    metrics_data = calculate_metrics(config["log_file"])
    metrics_data["webhook_stats"] = webhook_stats
    return jsonify(metrics_data)


@app.get("/stats")
def stats() -> Any:
    """Get human-readable trading statistics summary."""
    summary = get_trade_summary(config["log_file"])
    return jsonify({
        "summary": summary,
        "metrics": calculate_metrics(config["log_file"]),
        "webhook_stats": webhook_stats,
    })


@app.post("/webhook")
def webhook() -> Any:
    """Main webhook endpoint for TradingView alerts."""
    start_time = time.time()
    webhook_stats["total_requests"] += 1
    
    data = request.get_json(force=True, silent=True) or {}
    logger.info("=" * 60)
    logger.info("📥 WEBHOOK RECEIVED from %s", request.remote_addr)
    logger.info("📦 Payload: %s", data)

    signal = str(data.get("signal", "")).lower()
    auth_token = str(data.get("auth_token", ""))

    # Authentication check
    if auth_token != config["alert_auth_token"]:
        webhook_stats["invalid_auth"] += 1
        logger.warning("❌ Invalid auth token in alert: %s", auth_token)
        return jsonify({"status": "error", "detail": "Unauthorized: invalid auth_token"}), 401

    # Signal validation
    if signal not in {"buy", "sell"}:
        webhook_stats["invalid_signal"] += 1
        logger.warning("❌ Invalid signal: %s", signal)
        return jsonify({"status": "error", "detail": "Invalid signal"}), 400

    side = "BUY" if signal == "buy" else "SELL"
    symbol = config["symbol"]
    quantity = config["quantity"]
    
    logger.info("📊 Processing %s order: %s %s", side, quantity, symbol)

    # Initialize Binance client
    try:
        client = BinanceTestnetClient.from_env()
        logger.info("✅ Binance client initialized")
    except RuntimeError as e:
        webhook_stats["failed_trades"] += 1
        logger.error("❌ Configuration error: %s", e)
        return jsonify({"status": "error", "detail": str(e)}), 500

    # Place market order
    try:
        order_start = time.time()
        order = client.place_market_order(symbol=symbol, side=side, quantity=quantity)
        order_time = time.time() - order_start
        
        try:
            executed_qty = sum(float(fill.get("qty", 0.0)) for fill in order.get("fills", []))
            avg_price = sum(float(fill.get("price", 0.0)) * float(fill.get("qty", 0.0)) 
                          for fill in order.get("fills", [])) / executed_qty if executed_qty > 0 else 0.0
        except Exception:  # noqa: BLE001
            executed_qty = float(order.get("executedQty", 0.0))
            avg_price = float(order.get("price", 0.0)) if order.get("price") else 0.0
        
        # Log successful trade
        webhook_stats["successful_trades"] += 1
        logger.info("✅ ORDER EXECUTED successfully!")
        logger.info("   Order ID: %s", order.get("orderId"))
        logger.info("   Side: %s", side)
        logger.info("   Symbol: %s", symbol)
        logger.info("   Executed Qty: %s", executed_qty)
        logger.info("   Avg Price: $%.2f", avg_price)
        logger.info("   Execution Time: %.3f seconds", order_time)
        
        # Save to CSV
        trade_record = {
            "status": "success",
            "side": side,
            "symbol": symbol,
            "quantity": quantity,
            "executed_qty": executed_qty,
            "avg_price": avg_price,
            "order_id": order.get("orderId"),
            "client_order_id": order.get("clientOrderId"),
            "execution_time_seconds": round(order_time, 3),
            "tv_symbol": data.get("symbol", ""),
            "tv_exchange": data.get("exchange", ""),
            "tv_time": data.get("time", ""),
        }
        append_trade_to_csv(config["log_file"], trade_record)
        
        total_time = time.time() - start_time
        logger.info("💾 Trade recorded in %s (Total processing: %.3f seconds)", config["log_file"], total_time)
        logger.info("=" * 60)

        return jsonify(
            {
                "status": "success",
                "message": f"{side} market order executed on {symbol}",
                "order_id": order.get("orderId"),
                "side": side,
                "symbol": symbol,
                "executed_qty": executed_qty,
                "avg_price": avg_price,
                "execution_time_seconds": round(order_time, 3),
            }
        )
        
    except RuntimeError as e:
        webhook_stats["failed_trades"] += 1
        logger.error("❌ FAILED to place order: %s", e)
        
        # Log failed trade
        trade_record = {
            "status": "error",
            "side": side,
            "symbol": symbol,
            "quantity": quantity,
            "message": str(e),
            "tv_symbol": data.get("symbol", ""),
            "tv_exchange": data.get("exchange", ""),
            "tv_time": data.get("time", ""),
        }
        append_trade_to_csv(config["log_file"], trade_record)
        
        total_time = time.time() - start_time
        logger.error("💾 Failed trade logged (Total processing: %.3f seconds)", total_time)
        logger.info("=" * 60)
        
        return jsonify({"status": "error", "detail": f"Trade failed: {e}"}), 500


if __name__ == "__main__":
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("🚀 Starting Trading Bot Webhook Server")
    logger.info("=" * 60)
    logger.info("📡 Server: http://127.0.0.1:8001")
    logger.info("🔗 Webhook: http://127.0.0.1:8001/webhook")
    logger.info("📊 Metrics: http://127.0.0.1:8001/metrics")
    logger.info("📈 Stats: http://127.0.0.1:8001/stats")
    logger.info("=" * 60)
    
    # Print initial trade summary if CSV exists
    if os.path.exists(config["log_file"]):
        try:
            summary = get_trade_summary(config["log_file"])
            logger.info("\n%s", summary)
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not load initial metrics: %s", e)
    
    # Default to localhost:8001
    app.run(host="127.0.0.1", port=8001, debug=True)


