import logging
import os
from typing import Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.exchange.binance_client import BinanceTestnetClient
from app.models import TradingViewAlert, TradeResult
from app.storage import append_trade_to_csv


# Load environment variables from .env if present
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("trading_bot")

app = FastAPI(title="TradingView Webhook → Binance Testnet Bot")


def get_config() -> Dict[str, Any]:
    cfg = {
        "alert_auth_token": os.getenv("ALERT_AUTH_TOKEN", ""),
        "symbol": os.getenv("TRADING_SYMBOL", "BTCUSDT"),
        "quantity": float(os.getenv("TRADE_QUANTITY", "0.001")),
        "log_file": os.getenv("LOG_FILE", "logs/trades.csv"),
    }
    if not cfg["alert_auth_token"]:
        logger.warning("ALERT_AUTH_TOKEN is not set. All alerts will be rejected.")
    return cfg


config = get_config()


@app.get("/")
async def root() -> Dict[str, str]:
    return {"status": "ok", "message": "Trading bot webhook is running."}


@app.post("/webhook", response_model=TradeResult)
async def handle_webhook(alert: TradingViewAlert, request: Request) -> TradeResult:
    """
    Main webhook endpoint for TradingView alerts.

    Expects JSON body following `TradingViewAlert`.
    """
    logger.info("Received webhook from %s", request.client.host if request.client else "unknown")
    logger.info("Payload: %s", alert.dict())

    # 1. Auth check
    if alert.auth_token != config["alert_auth_token"]:
        logger.warning("Invalid auth token in alert: %s", alert.auth_token)
        raise HTTPException(status_code=401, detail="Unauthorized: invalid auth_token")

    # 2. Map signal to side
    side = "BUY" if alert.signal == "buy" else "SELL"

    # 3. Use configured symbol and quantity (TradingView symbol is logged but not trusted)
    symbol = config["symbol"]
    quantity = config["quantity"]

    try:
        client = BinanceTestnetClient.from_env()
    except RuntimeError as e:
        logger.error("Configuration error: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e

    # 4. Attempt to place market order
    try:
        order = client.place_market_order(symbol=symbol, side=side, quantity=quantity)
    except RuntimeError as e:
        logger.error("Failed to place order: %s", e)
        # Log failed attempt as well
        append_trade_to_csv(
            config["log_file"],
            {
                "status": "error",
                "side": side,
                "symbol": symbol,
                "quantity": quantity,
                "message": str(e),
                "tv_symbol": alert.symbol or "",
                "tv_exchange": alert.exchange or "",
                "tv_time": alert.time or "",
            },
        )
        raise HTTPException(status_code=500, detail=f"Trade failed: {e}") from e

    executed_qty = 0.0
    try:
        executed_qty = sum(float(fill.get("qty", 0.0)) for fill in order.get("fills", []))
    except Exception:  # noqa: BLE001
        executed_qty = float(order.get("executedQty", 0.0))

    # 5. Log successful trade to CSV
    append_trade_to_csv(
        config["log_file"],
        {
            "status": "success",
            "side": side,
            "symbol": symbol,
            "quantity": quantity,
            "executed_qty": executed_qty,
            "order_id": order.get("orderId"),
            "client_order_id": order.get("clientOrderId"),
            "tv_symbol": alert.symbol or "",
            "tv_exchange": alert.exchange or "",
            "tv_time": alert.time or "",
        },
    )

    logger.info("Trade recorded in %s", config["log_file"])

    return TradeResult(
        status="success",
        message=f"{side} market order executed on {symbol}",
        order_id=order.get("orderId"),
        side=side,
        symbol=symbol,
        executed_qty=executed_qty,
    )


@app.exception_handler(Exception)  # noqa: BLE001
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled server error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


