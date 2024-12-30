import asyncio
import json
import os

from dotenv import load_dotenv
from aiohttp import ClientSession
from hexbytes import HexBytes
from web3 import Web3, HTTPProvider
from web3.types import BlockData

from suspicion import SuspicionType, SuspicionStatus, SuspectedReentrancy

load_dotenv()


class BlockAnalyzer:
    PROVIDER_URL = f"https://lb.drpc.org/ogrpc?network=ethereum&dkey={os.getenv("API_KEY")}"
    UNSINGED_URL = "https://eth.drpc.org"

    def __init__(self, session: ClientSession):
        self._web3_eth = Web3(HTTPProvider(self.PROVIDER_URL)).eth
        self._session = session

    def _get_latest_block(self) -> BlockData:
        return self._web3_eth.get_block("latest", full_transactions=True)

    @staticmethod
    def _get_smart_contract_transactions(block: BlockData) -> list[dict]:

        # Assume that if "input" is not empty, this is probably a smart contract invocation. Not sure about this
        # I can check for each one its codeSize, but maybe it is too slow?
        def is_smart_contract(transaction: dict):
            data: HexBytes = transaction["input"]
            return not data == HexBytes("0x")

        # Type hinting seems to be broken here, in the library "transactions" is a sequence of Hexbytes,
        # but in reality it is a sequence of dictionaries
        return [
            transaction
            for transaction in block["transactions"]
            if is_smart_contract(transaction)
        ]  # ignore pep

    async def _get_debug_information_for_transaction(self, transaction) -> dict:
        params = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "debug_traceTransaction",
            "params": ["0x" + transaction["hash"].hex(), {"tracer": "callTracer"}],
        }
        async with self._session.post(
            self.UNSINGED_URL, data=json.dumps(params)
        ) as response:
            return await response.json()

    async def _analyze_singular_transaction(
        self, transaction
    ) -> SuspectedReentrancy | None:
        debug_info = await self._get_debug_information_for_transaction(transaction)
        try:
            transaction_calls = debug_info["result"]["calls"]
        except KeyError:
            return

        # How to find reentrancy.
        # Simple algorithm - follow call stack, if a caller contract is called, as a result of its own call, through
        # a different contract, it is first defined as light suspicion of reentrancy.
        #
        # Hard suspicion - if the same function is also being called

        # For each contract, the functions it has called
        calling_context = {}
        suspicion_status = SuspicionStatus(SuspicionType.NONE)
        self._analyze_call_stack(transaction_calls, calling_context, suspicion_status)

        if suspicion_status.sus is not SuspicionType.NONE:
            return SuspectedReentrancy(
                transaction=transaction["hash"], type=suspicion_status.sus
            )
        else:
            return None

    # Recursively go over calls
    @staticmethod
    def _analyze_call_stack(
        calls: list, calling_context: dict, suspicion_status: SuspicionStatus
    ) -> None:
        for call in calls:
            target = call["to"]
            # extremely hideous, get the first 4 bytes (hex representation, 8 characters + 2 for '0x'), representing
            # the function called
            called_function = call["input"][:10]
            try:
                called_by_target_contract = calling_context[target]
                if called_function in called_by_target_contract:
                    suspicion_status.found_suspicion(SuspicionType.HARD)
                else:
                    suspicion_status.found_suspicion(SuspicionType.LIGHT)
                    calling_context[target].append(called_function)

            except KeyError:
                calling_context[target] = [called_function]

            try:
                BlockAnalyzer._analyze_call_stack(
                    call["calls"], calling_context, suspicion_status
                )
            except KeyError:
                pass

            calling_context[target].remove(called_function)
            if not calling_context[target]:
                del calling_context[target]

    async def analyze_block(self) -> list[SuspectedReentrancy]:
        latest = self._get_latest_block()
        transactions = self._get_smart_contract_transactions(latest)

        requests = [
            self._analyze_singular_transaction(transaction)
            for transaction in transactions
        ]
        suspicions = await asyncio.gather(*requests)
        suspicions = [sus for sus in suspicions if sus is not None]

        return suspicions
