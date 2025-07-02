import asyncio
import websockets
import json
import os
import logging
from typing import Set
import signal
import sys

from service_layer import service, uow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FilingListener:
    def __init__(self):
        self.api_key = os.getenv("SEC_API_KEY")
        self.server_url = "wss://stream.sec-api.io"
        self.ws_endpoint = f"{self.server_url}?apiKey={self.api_key}"
        self.background_tasks: Set[asyncio.Task] = set()
        self.running = True

    async def process_filing(self, filing_data: dict):
        try:
            logger.info(f"Processing {filing_data['formType']} filing for CIK: {filing_data['cik']}")

            ticker = filing_data.get('ticker')
            if not ticker:
                logger.warning(f"No ticker found for CIK: {filing_data['cik']}")
                return

            uow_instance = uow.SqlAlchemyUnitOfWork()

            result = service.get_consolidated_income_statements(
                ticker=ticker,
                uow_instance=uow_instance,
                form_type=filing_data['formType'],
                retrieve_from_database=False,
                overwrite_database=True
            )

            logger.info(f"Successfully processed {filing_data['formType']} for {ticker}")
            logger.info(f"Statements count: {len(result.statements) if result.statements else 0}")

        except Exception as e:
            logger.error(f"Error processing filing: {e}", exc_info=True)

    async def send_ping(self, websocket):
        while self.running:
            try:
                pong_waiter = await websocket.ping()
                await asyncio.wait_for(pong_waiter, timeout=5)
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Error sending ping: {e}")
                await websocket.close()
                return

    async def listen_for_filings(self):
        retry_counter = 0
        max_retries = 10

        while retry_counter < max_retries and self.running:
            try:
                async with websockets.connect(self.ws_endpoint) as websocket:
                    logger.info(f"Connected to: {self.server_url}")
                    retry_counter = 0

                    ping_task = asyncio.create_task(self.send_ping(websocket))

                    while self.running:
                        message = await websocket.recv()
                        filings = json.loads(message)

                        for filing in filings:
                            logger.info(f"📄 {filing['accessionNo']} {filing['formType']} {filing['filedAt']} CIK:{filing['cik']}")

                            if filing['formType'] in ['10-K']:
                                logger.info(f"🎯 Found {filing['formType']} filing! Starting background processing...")

                                task = asyncio.create_task(self.process_filing(filing))
                                self.background_tasks.add(task)
                                task.add_done_callback(self.background_tasks.discard)

            except Exception as e:
                retry_counter += 1
                logger.error(f"Connection error: {e}")
                logger.info(f"Reconnecting in 10 sec... (Attempt {retry_counter}/{max_retries})")

                await asyncio.sleep(10)

        logger.error("Maximum reconnection attempts reached. Stopping listener.")

    def shutdown(self):
        logger.info("Shutting down filing listener...")
        self.running = False

async def main():
    listener = FilingListener()

    def signal_handler(signum, frame):
        listener.shutdown()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        await listener.listen_for_filings()
    finally:
        if listener.background_tasks:
            logger.info(f"Waiting for {len(listener.background_tasks)} background tasks...")
            await asyncio.gather(*listener.background_tasks, return_exceptions=True)

if __name__ == "__main__":
    asyncio.run(main())
