from __future__ import annotations

import logging
import os
import time
from typing import Literal, Optional, Dict, Any

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException


logger = logging.getLogger(__name__)


class BinanceTestnetClient:
    """
    Simple wrapper around `python-binance` for Binance Spot Testnet.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str,
    ) -> None:
        self.client = Client(api_key, api_secret, testnet=True)
        # Override base URL if provided (for some python-binance versions)
        if base_url:
            self.client.API_URL = base_url
        # Increase recvWindow to handle clock drift (default is 5000ms, use 60000ms max)
        self.client.recv_window = 60000
        # Sync time offset with Binance server
        self._sync_time_offset()

    @classmethod
    def from_env(cls) -> "BinanceTestnetClient":
        api_key = os.getenv("BINANCE_API_KEY", "")
        api_secret = os.getenv("BINANCE_API_SECRET", "")
        base_url = os.getenv("BINANCE_TESTNET_BASE_URL", "https://testnet.binance.vision")

        if not api_key or not api_secret:
            raise RuntimeError("BINANCE_API_KEY and BINANCE_API_SECRET must be set in environment.")

        return cls(api_key=api_key, api_secret=api_secret, base_url=base_url)

    def _sync_time_offset(self) -> None:
        """Sync time offset with Binance server to avoid timestamp errors."""
        try:
            # Get server time
            server_time_info = self.client.get_server_time()
            server_time = server_time_info['serverTime']
            
            # Calculate offset (difference between server time and local time)
            local_time = int(time.time() * 1000)  # Convert to milliseconds
            time_offset = server_time - local_time
            
            # Set the time offset on the client
            self.client.timestamp_offset = time_offset
            
            logger.info("Synced time offset: %d ms (server ahead by %d ms)", time_offset, abs(time_offset))
        except Exception as e:  # noqa: BLE001
            logger.warning("Could not sync time offset with Binance: %s. Continuing anyway...", e)
            # Set a default offset of 0 if sync fails
            self.client.timestamp_offset = 0

    def place_market_order(
        self,
        symbol: str,
        side: Literal["BUY", "SELL"],
        quantity: float,
    ) -> Dict[str, Any]:
        """
        Place a market order on Binance Spot Testnet.

        Returns the full Binance response or raises an informative error.
        """
        try:
            logger.info("📤 Placing %s market order: %s %s", side, quantity, symbol)
            # Re-sync time offset before placing order (in case it drifted)
            self._sync_time_offset()
            
            order_start = time.time()
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type=Client.ORDER_TYPE_MARKET,
                quantity=quantity,
                recvWindow=60000,  # 60 second window (max allowed) to handle clock drift
            )
            order_time = time.time() - order_start
            
            logger.info("✅ Order executed successfully in %.3f seconds", order_time)
            logger.debug("📋 Full Binance response: %s", order)
            return order
        except BinanceAPIException as e:
            # API related error, e.g. no balance, invalid symbol, etc.
            logger.error("BinanceAPIException: %s", e)
            raise RuntimeError(f"Binance API error: {e.message}") from e
        except BinanceRequestException as e:
            # Network or request related error
            logger.error("BinanceRequestException: %s", e)
            raise RuntimeError("Network error communicating with Binance Testnet.") from e
        except Exception as e:  # noqa: BLE001
            logger.exception("Unexpected error placing Binance order")
            raise RuntimeError(f"Unexpected error placing Binance order: {e}") from e


