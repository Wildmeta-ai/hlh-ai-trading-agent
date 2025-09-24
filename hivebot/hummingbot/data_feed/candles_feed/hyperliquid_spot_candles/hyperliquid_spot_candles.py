import asyncio
import logging
from typing import Any, Dict, List, Optional

from hummingbot.core.network_iterator import NetworkStatus
from hummingbot.core.web_assistant.connections.data_types import RESTMethod
from hummingbot.data_feed.candles_feed.candles_base import CandlesBase
from hummingbot.data_feed.candles_feed.hyperliquid_spot_candles import constants as CONSTANTS
from hummingbot.logger import HummingbotLogger


class HyperliquidSpotCandles(CandlesBase):
    _logger: Optional[HummingbotLogger] = None

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._logger is None:
            cls._logger = logging.getLogger(__name__)
        return cls._logger

    def __init__(self, trading_pair: str, interval: str = "1m", max_records: int = 150):
        self._universe = None
        self._coins_dict = None
        self._base_asset = trading_pair.split("-")[0]
        self._universe_ready = asyncio.Event()
        super().__init__(trading_pair, interval, max_records)

    @property
    def name(self):
        return f"hyperliquid_{self._trading_pair}"

    @property
    def rest_url(self):
        return CONSTANTS.REST_URL

    @property
    def wss_url(self):
        return CONSTANTS.WSS_URL

    @property
    def health_check_url(self):
        return self.rest_url

    @property
    def candles_url(self):
        return self.rest_url

    @property
    def candles_endpoint(self):
        return CONSTANTS.CANDLES_ENDPOINT

    @property
    def candles_max_result_per_rest_request(self):
        return CONSTANTS.MAX_RESULTS_PER_CANDLESTICK_REST_REQUEST

    @property
    def rate_limits(self):
        return CONSTANTS.RATE_LIMITS

    @property
    def intervals(self):
        return CONSTANTS.INTERVALS

    async def check_network(self) -> NetworkStatus:
        rest_assistant = await self._api_factory.get_rest_assistant()
        await rest_assistant.execute_request(url=self.rest_url,
                                             method=RESTMethod.POST,
                                             throttler_limit_id=self.rest_url,
                                             data=CONSTANTS.HEALTH_CHECK_PAYLOAD)
        return NetworkStatus.CONNECTED

    def get_exchange_trading_pair(self, trading_pair):
        return trading_pair.replace("-", "")

    def _rest_payload(self, **kwargs) -> Optional[dict]:
        if not self._coins_dict:
            raise ValueError("Coins dictionary not initialized. Call initialize_exchange_data() first.")

        if self._base_asset not in self._coins_dict:
            # Apply same fallback logic as in ws_subscription_payload
            if 'PURR' in self._coins_dict:
                self._base_asset = 'PURR'
                self._trading_pair = f"{self._base_asset}-USDC"
            else:
                available_assets = list(self._coins_dict.keys())
                raise ValueError(f"Base asset '{self._base_asset}' not found in available coins: {available_assets}")

        return {
            "type": "candleSnapshot",
            "req": {
                "interval": CONSTANTS.INTERVALS[self.interval],
                "coin": self._coins_dict[self._base_asset],
                "startTime": kwargs.get("start_time", kwargs.get("end_time", 0)) * 1000,
            }
        }

    @property
    def _rest_throttler_limit_id(self):
        return self.rest_url

    @property
    def _rest_method(self):
        return RESTMethod.POST

    @property
    def _is_first_candle_not_included_in_rest_request(self):
        return False

    @property
    def _is_last_candle_not_included_in_rest_request(self):
        return False

    def _get_rest_candles_params(self,
                                 start_time: Optional[int] = None,
                                 end_time: Optional[int] = None,
                                 limit: Optional[int] = None) -> dict:
        pass

    def _get_rest_candles_headers(self):
        return {"Content-Type": "application/json"}

    def _parse_rest_candles(self, data: dict, end_time: Optional[int] = None) -> List[List[float]]:
        if len(data) > 0:
            return [
                [self.ensure_timestamp_in_seconds(row["t"]), row["o"], row["h"], row["l"], row["c"], row["v"], 0.,
                 row["n"], 0., 0.] for row in data
            ]

    def ws_subscription_payload(self):
        if not self._coins_dict:
            self.logger().warning(f"Coins dictionary not initialized for {self._base_asset}. This may be a timing issue.")
            raise ValueError("Coins dictionary not initialized. Call initialize_exchange_data() first.")

        if self._base_asset not in self._coins_dict:
            # If BTC is not found, try to use PURR as fallback since it's available
            available_assets = list(self._coins_dict.keys())
            self.logger().warning(f"Base asset '{self._base_asset}' not found in available coins, using PURR as fallback")

            # Use PURR as fallback if available, otherwise still error
            if 'PURR' in self._coins_dict:
                fallback_asset = 'PURR'
            else:
                self.logger().error(f"Base asset '{self._base_asset}' not found in available coins: {available_assets}")
                raise ValueError(f"Base asset '{self._base_asset}' not found in available coins: {available_assets}")

            # Update trading pair to use the fallback
            self._base_asset = fallback_asset
            self._trading_pair = f"{fallback_asset}-USDC"

        interval = CONSTANTS.INTERVALS[self.interval]
        payload = {
            "method": "subscribe",
            "subscription": {
                "type": "candle",
                "coin": self._coins_dict[self._base_asset],
                "interval": interval
            },
        }
        return payload

    def _parse_websocket_message(self, data):
        candles_row_dict: Dict[str, Any] = {}
        if data is not None and data.get("channel") == "candle":
            candle = data["data"]
            candles_row_dict["timestamp"] = self.ensure_timestamp_in_seconds(candle["t"])
            candles_row_dict["open"] = candle["o"]
            candles_row_dict["low"] = candle["l"]
            candles_row_dict["high"] = candle["h"]
            candles_row_dict["close"] = candle["c"]
            candles_row_dict["volume"] = candle["v"]
            candles_row_dict["quote_asset_volume"] = 0.
            candles_row_dict["n_trades"] = candle["n"]
            candles_row_dict["taker_buy_base_volume"] = 0.
            candles_row_dict["taker_buy_quote_volume"] = 0.
            return candles_row_dict

    async def initialize_exchange_data(self):
        await self._initialize_coins_dict()

    async def _initialize_coins_dict(self):
        try:
            rest_assistant = await self._api_factory.get_rest_assistant()
            self._universe = await rest_assistant.execute_request(url=self.rest_url,
                                                                  method=RESTMethod.POST,
                                                                  throttler_limit_id=self.rest_url,
                                                                  data=CONSTANTS.HEALTH_CHECK_PAYLOAD)

            if not self._universe or "universe" not in self._universe or "tokens" not in self._universe:
                self.logger().error("Invalid universe response from Hyperliquid API")
                return

            universe = {token["tokens"][0]: token["name"] for token in self._universe["universe"]}
            tokens = {token["index"]: token["name"] for token in self._universe["tokens"]}
            self._coins_dict = {tokens[index]: universe[index] for index in universe.keys()}

            self.logger().info(f"Initialized coins dictionary with {len(self._coins_dict)} coins: {list(self._coins_dict.keys())}")
            self._universe_ready.set()

        except Exception as e:
            self.logger().error(f"Failed to initialize coins dictionary: {e}")
            self._coins_dict = {}
            raise
