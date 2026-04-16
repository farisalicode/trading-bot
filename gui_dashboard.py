"""
Trading Bot GUI Dashboard

A graphical interface to monitor trading bot performance, metrics, and trade history.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
from datetime import datetime
from pathlib import Path
import json

from app.metrics import calculate_metrics, load_trades_from_csv
from dotenv import load_dotenv
import os

load_dotenv()


class TradingBotDashboard:
    """Main GUI application for trading bot monitoring."""

    def __init__(self, root):
        self.root = root
        self.root.title("Trading Bot Dashboard")
        self.root.geometry("1200x800")
        self.root.configure(bg="#1e1e1e")

        # Configuration
        self.csv_path = os.getenv("LOG_FILE", "logs/trades.csv")
        self.refresh_interval = 2  # seconds

        # Create UI
        self.create_widgets()

        # Start auto-refresh
        self.refresh_data()
        self.auto_refresh()

    def create_widgets(self):
        """Create all GUI widgets."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Title
        title_label = tk.Label(
            main_frame,
            text="🤖 Trading Bot Dashboard",
            font=("Arial", 20, "bold"),
            bg="#1e1e1e",
            fg="#4CAF50",
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # Left column - Metrics
        metrics_frame = ttk.LabelFrame(main_frame, text="📊 Performance Metrics", padding="10")
        metrics_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        self.metrics_text = tk.Text(
            metrics_frame,
            width=40,
            height=15,
            font=("Consolas", 10),
            bg="#2d2d2d",
            fg="#ffffff",
            relief=tk.FLAT,
            wrap=tk.WORD,
        )
        self.metrics_text.pack(fill=tk.BOTH, expand=True)

        # Middle column - Recent Trades
        trades_frame = ttk.LabelFrame(main_frame, text="📈 Recent Trades", padding="10")
        trades_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        # Treeview for trades
        columns = ("Time", "Side", "Symbol", "Qty", "Price", "Status", "Order ID")
        self.trades_tree = ttk.Treeview(trades_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.trades_tree.heading(col, text=col)
            self.trades_tree.column(col, width=100)

        scrollbar_trades = ttk.Scrollbar(trades_frame, orient=tk.VERTICAL, command=self.trades_tree.yview)
        self.trades_tree.configure(yscrollcommand=scrollbar_trades.set)
        
        self.trades_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_trades.pack(side=tk.RIGHT, fill=tk.Y)

        # Right column - Logs
        logs_frame = ttk.LabelFrame(main_frame, text="📝 Activity Logs", padding="10")
        logs_frame.grid(row=1, column=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.logs_text = scrolledtext.ScrolledText(
            logs_frame,
            width=50,
            height=15,
            font=("Consolas", 9),
            bg="#2d2d2d",
            fg="#00ff00",
            relief=tk.FLAT,
            wrap=tk.WORD,
        )
        self.logs_text.pack(fill=tk.BOTH, expand=True)

        # Bottom - Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))

        self.status_label = tk.Label(
            status_frame,
            text="🟢 Ready | Last Update: --",
            font=("Arial", 10),
            bg="#1e1e1e",
            fg="#ffffff",
            anchor=tk.W,
        )
        self.status_label.pack(side=tk.LEFT)

        self.refresh_button = tk.Button(
            status_frame,
            text="🔄 Refresh Now",
            command=self.refresh_data,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            relief=tk.FLAT,
            padx=10,
            pady=5,
        )
        self.refresh_button.pack(side=tk.RIGHT)

        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=1)
        main_frame.rowconfigure(1, weight=1)

    def format_metrics(self, metrics: dict) -> str:
        """Format metrics for display."""
        lines = [
            "╔═══════════════════════════════╗",
            "║   TRADING BOT METRICS         ║",
            "╠═══════════════════════════════╣",
            f"║ Total Trades:      {metrics['total_trades']:>6}  ║",
            f"║ Successful:         {metrics['successful_trades']:>6}  ║",
            f"║ Failed:            {metrics['failed_trades']:>6}  ║",
            f"║ Success Rate:      {metrics['success_rate']:>5.1f}%  ║",
            "╠═══════════════════════════════╣",
            f"║ Buy Orders:        {metrics['buy_count']:>6}  ║",
            f"║ Sell Orders:       {metrics['sell_count']:>6}  ║",
            f"║ Total Volume:  {metrics['total_volume']:>10.8f} ║",
            "╚═══════════════════════════════╝",
        ]
        return "\n".join(lines)

    def refresh_data(self):
        """Refresh all data from CSV and logs."""
        try:
            # Update metrics
            metrics = calculate_metrics(self.csv_path)
            metrics_text = self.format_metrics(metrics)
            
            self.metrics_text.delete(1.0, tk.END)
            self.metrics_text.insert(1.0, metrics_text)

            # Update recent trades
            self.trades_tree.delete(*self.trades_tree.get_children())
            recent_trades = metrics.get("recent_trades", [])
            
            for trade in recent_trades[-20:]:  # Show last 20 trades
                timestamp = trade.get("timestamp", trade.get("tv_time", "N/A"))
                side = trade.get("side", "N/A")
                symbol = trade.get("symbol", "N/A")
                qty = trade.get("executed_qty", trade.get("quantity", "N/A"))
                price = trade.get("avg_price", "N/A")
                status = trade.get("status", "N/A")
                order_id = str(trade.get("order_id", "N/A"))

                # Format values
                if isinstance(qty, (int, float)):
                    qty = f"{qty:.8f}"
                if isinstance(price, (int, float)):
                    price = f"${price:,.2f}" if price > 0 else "N/A"
                
                # Color coding
                tags = []
                if status == "success":
                    tags.append("success")
                elif status == "error":
                    tags.append("error")
                if side == "BUY":
                    tags.append("buy")
                elif side == "SELL":
                    tags.append("sell")

                self.trades_tree.insert(
                    "",
                    tk.END,
                    values=(timestamp[:19] if len(timestamp) > 19 else timestamp, side, symbol, qty, price, status.upper(), order_id),
                    tags=tags,
                )

            # Configure tag colors
            self.trades_tree.tag_configure("success", foreground="#4CAF50")
            self.trades_tree.tag_configure("error", foreground="#f44336")
            self.trades_tree.tag_configure("buy", background="#1e3a1e")
            self.trades_tree.tag_configure("sell", background="#3a1e1e")

            # Update logs
            self.update_logs()

            # Update status
            now = datetime.now().strftime("%H:%M:%S")
            self.status_label.config(text=f"🟢 Connected | Last Update: {now}")

        except FileNotFoundError:
            self.metrics_text.delete(1.0, tk.END)
            self.metrics_text.insert(1.0, "No trade data found.\n\nWaiting for trades...")
            self.status_label.config(text="🟡 Waiting for data...")
        except Exception as e:
            self.status_label.config(text=f"🔴 Error: {str(e)}")

    def update_logs(self):
        """Update logs from log file."""
        log_file = Path("logs/trading_bot.log")
        if log_file.exists():
            try:
                # Read last 50 lines
                with log_file.open("r", encoding="utf-8") as f:
                    lines = f.readlines()
                    recent_lines = lines[-50:]  # Last 50 lines
                
                self.logs_text.delete(1.0, tk.END)
                self.logs_text.insert(1.0, "".join(recent_lines))
                self.logs_text.see(tk.END)  # Scroll to bottom
            except Exception:
                pass

    def auto_refresh(self):
        """Auto-refresh data periodically."""
        self.refresh_data()
        self.root.after(int(self.refresh_interval * 1000), self.auto_refresh)


def main():
    """Launch the GUI dashboard."""
    root = tk.Tk()
    app = TradingBotDashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()

