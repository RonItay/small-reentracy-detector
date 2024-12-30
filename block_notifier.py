import json
import os

from dotenv import load_dotenv
from time import sleep
from typing import Callable
from web3 import Web3, HTTPProvider
from websocket import WebSocketApp

load_dotenv()


class BlockListener:
    PROVIDER_URL = f"https://lb.drpc.org/ogrpc?network=ethereum&dkey={os.getenv("API_KEY")}"

    def __init__(self, on_new_block_callback: Callable):
        self._callback = on_new_block_callback
        self._http_web3_eth = Web3(HTTPProvider(self.PROVIDER_URL)).eth

    async def listen(self):
        raise NotImplementedError()


class PullBlockListener(BlockListener):
    TIME_BETWEEN_CHECKS = 1  # seconds

    def __init__(self, on_new_block_callback):
        super().__init__(on_new_block_callback)

        # Setting here to 0 means that the current block will also be checked, which is good.
        self._last_block_checked = 0

    async def _wait_for_new_block(self) -> int:
        while True:
            curr_block = self._http_web3_eth.block_number  # Why is this blocking and not awaitable?
            if curr_block != self._last_block_checked:
                self._last_block_checked = curr_block
                return curr_block
            else:
                sleep(self.TIME_BETWEEN_CHECKS)

    async def listen(self):
        while True:
            await self._wait_for_new_block()
            await self._callback()


# Uses subscriptions, which doesn't really work honestly.
# Connections seems to constantly close if you're using the unsigned API (no API key),
# And the API to sign to subscriptions doesn't seem to be enabled for free accounts.

# Currently this is broken, as this websocket framework doesnt really allow me to run async functions on callback.
# There is ofcourse a way to make it work, but since the subscription service seems a bit broken - I wont work on in
# further
class PushBlockListener(BlockListener):
    class ConnectionClosedException(Exception):
        pass

    UNSIGNED_WEBSOCKET_URL = 'wss://eth.drpc.org'

    def __init__(self, on_new_block_callback):
        super().__init__(on_new_block_callback)
        self._ws = self._get_websocket()

        self._last_block_checked = 0

    def _get_websocket(self):
        def _on_open(ws):
            SUBSCRIPTION_REQUEST = {
                "jsonrpc": "2.0",
                "method": "eth_subscribe",
                "params": ["newHeads"],
                "id": 1
            }
            ws.send(json.dumps(SUBSCRIPTION_REQUEST))

        def _on_close(ws, close_status_code, close_msg):
            pass

        def _on_message(ws, msg):
            msg = json.loads(msg)

            if msg.get("method") != "eth_subscription":
                return

            current_block = int(msg["params"]["result"]["number"], 16)

            if current_block == self._last_block_checked:
                return

            self._last_block_checked = current_block
            self._callback()

        def _on_error(ws, error):
            raise self.ConnectionClosedException()

        return WebSocketApp(
            self.UNSIGNED_WEBSOCKET_URL,
            on_open=_on_open,
            on_message=_on_message,
            on_error=_on_error,
            on_close=_on_close,
        )

    async def listen(self):
        # Fast way to get blocked
        while True:
            try:
                self._ws.run_forever()
            except self.ConnectionClosedException:
                print("Closed")
