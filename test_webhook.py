"""
Manual webhook tester for TradingView alerts.

Use this script to manually test your webhook endpoint when TradingView
webhooks are not available (free account limitation).

Run: python test_webhook.py
"""

import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
WEBHOOK_URL = "http://127.0.0.1:8001/webhook"
AUTH_TOKEN = os.getenv("ALERT_AUTH_TOKEN", "your_secret_here")

def test_buy_signal():
    """Test a BUY signal webhook."""
    payload = {
        "signal": "buy",
        "symbol": "BTCUSDT",
        "exchange": "BINANCE",
        "time": "2025-12-04 12:00:00",
        "auth_token": AUTH_TOKEN
    }
    
    print("Testing BUY signal...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("\nERROR: Could not connect to webhook server.")
        print("Make sure server.py is running on http://127.0.0.1:8001")
        return False
    except Exception as e:
        print(f"\nERROR: {e}")
        return False

def test_sell_signal():
    """Test a SELL signal webhook."""
    payload = {
        "signal": "sell",
        "symbol": "BTCUSDT",
        "exchange": "BINANCE",
        "time": "2025-12-04 12:00:00",
        "auth_token": AUTH_TOKEN
    }
    
    print("\nTesting SELL signal...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("\nERROR: Could not connect to webhook server.")
        print("Make sure server.py is running on http://127.0.0.1:8001")
        return False
    except Exception as e:
        print(f"\nERROR: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TradingView Webhook Tester")
    print("=" * 60)
    print(f"Webhook URL: {WEBHOOK_URL}")
    print(f"Auth Token: {AUTH_TOKEN[:10]}..." if len(AUTH_TOKEN) > 10 else f"Auth Token: {AUTH_TOKEN}")
    print("=" * 60)
    
    # Test both signals
    buy_ok = test_buy_signal()
    sell_ok = test_sell_signal()
    
    print("\n" + "=" * 60)
    if buy_ok and sell_ok:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed. Check the errors above.")
    print("=" * 60)

