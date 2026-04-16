from pydantic import BaseModel
from typing import Optional


class TradingViewAlert(BaseModel):
    """
    Expected JSON payload from TradingView webhook.

    Example:
    {
      "signal": "buy",
      "symbol": "BTCUSDT",
      "exchange": "BINANCE",
      "time": "2025-12-04 12:34:56",
      "auth_token": "super_secret_alert_token"
    }
    """

    signal: str
    symbol: Optional[str] = None
    exchange: Optional[str] = None
    time: Optional[str] = None
    auth_token: str


class TradeResult(BaseModel):
    status: str
    message: str
    order_id: Optional[int] = None
    side: Optional[str] = None
    symbol: Optional[str] = None
    executed_qty: Optional[float] = None


