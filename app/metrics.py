"""
Trade metrics and statistics tracking.

Calculates performance metrics from trade history.
"""

import csv
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


def load_trades_from_csv(csv_path: str) -> List[Dict[str, Any]]:
    """Load all trades from CSV file."""
    path = Path(csv_path)
    if not path.exists():
        return []
    
    trades = []
    with path.open(mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            trades.append(row)
    
    return trades


def calculate_metrics(csv_path: str) -> Dict[str, Any]:
    """
    Calculate trading metrics from CSV trade history.
    
    Returns:
        Dictionary with metrics including:
        - total_trades: Total number of trades
        - successful_trades: Number of successful trades
        - failed_trades: Number of failed trades
        - buy_count: Number of BUY orders
        - sell_count: Number of SELL orders
        - total_volume: Total volume traded
        - success_rate: Percentage of successful trades
        - recent_trades: Last 10 trades
    """
    trades = load_trades_from_csv(csv_path)
    
    if not trades:
        return {
            "total_trades": 0,
            "successful_trades": 0,
            "failed_trades": 0,
            "buy_count": 0,
            "sell_count": 0,
            "total_volume": 0.0,
            "success_rate": 0.0,
            "recent_trades": [],
        }
    
    successful = [t for t in trades if t.get("status") == "success"]
    failed = [t for t in trades if t.get("status") == "error"]
    buys = [t for t in successful if t.get("side") == "BUY"]
    sells = [t for t in successful if t.get("side") == "SELL"]
    
    # Calculate total volume
    total_volume = 0.0
    for trade in successful:
        try:
            qty = float(trade.get("executed_qty", trade.get("quantity", 0)))
            total_volume += qty
        except (ValueError, TypeError):
            pass
    
    success_rate = (len(successful) / len(trades) * 100) if trades else 0.0
    
    # Get recent trades (last 10)
    recent = trades[-10:] if len(trades) > 10 else trades
    recent.reverse()  # Most recent first
    
    return {
        "total_trades": len(trades),
        "successful_trades": len(successful),
        "failed_trades": len(failed),
        "buy_count": len(buys),
        "sell_count": len(sells),
        "total_volume": round(total_volume, 8),
        "success_rate": round(success_rate, 2),
        "recent_trades": recent,
    }


def get_trade_summary(csv_path: str) -> str:
    """
    Generate a human-readable summary of trading activity.
    
    Returns:
        Formatted string with trade statistics.
    """
    metrics = calculate_metrics(csv_path)
    
    summary = f"""
╔══════════════════════════════════════════════════════════╗
║              TRADING BOT PERFORMANCE METRICS             ║
╠══════════════════════════════════════════════════════════╣
║ Total Trades:        {metrics['total_trades']:>6}                              ║
║ Successful:          {metrics['successful_trades']:>6}                              ║
║ Failed:              {metrics['failed_trades']:>6}                              ║
║ Success Rate:        {metrics['success_rate']:>5.1f}%                            ║
╠══════════════════════════════════════════════════════════╣
║ Buy Orders:          {metrics['buy_count']:>6}                              ║
║ Sell Orders:         {metrics['sell_count']:>6}                              ║
║ Total Volume:        {metrics['total_volume']:>10.8f} BTC                      ║
╚══════════════════════════════════════════════════════════╝
"""
    return summary

