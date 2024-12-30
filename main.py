import asyncio
import os

from aiohttp import ClientSession
from dotenv import load_dotenv

from block_analyzer import BlockAnalyzer
from block_notifier import PullBlockListener
from suspicion import SuspectedReentrancy

load_dotenv()


API_KEY = os.getenv("API_KEY")


def pretty_print_suspicions(suspicions: list[SuspectedReentrancy]):
    pretty_print_suspicion_format = (
        "transaction: {trans_hash}, suspicion_level: {suspicion_level}"
    )
    print(
        "\n".join(
            [
                pretty_print_suspicion_format.format(
                    trans_hash=sus.transaction.hex(), suspicion_level=sus.type.name
                )
                for sus in suspicions
            ]
        )
    )


async def main():
    async def _analyze_blocks_callback():
        async with ClientSession() as session:
            suspicions = await BlockAnalyzer(session).analyze_block()
            pretty_print_suspicions(suspicions)

    listener = PullBlockListener(_analyze_blocks_callback)
    await listener.listen()


if __name__ == "__main__":
    asyncio.run(main())
