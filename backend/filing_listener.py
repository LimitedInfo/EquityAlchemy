import asyncio
import websockets
import json
import os
import sys
import os
os.chdir('../backend')

from service_layer import service, uow

API_KEY = os.getenv("SEC_API_KEY")
SERVER_URL = "wss://stream.sec-api.io"
WS_ENDPOINT = SERVER_URL + "?apiKey=" + API_KEY

async def process_10k_filing(filing_data):
    """Process a 10-K filing in the background"""
    try:


                # Create UoW instance
        uow_instance = uow.SqlAlchemyUnitOfWork()

        # You'll need to map CIK to ticker - this is a simplified example
        # In practice, you might need a CIK-to-ticker mapping service
        with uow_instance as uow_sqlalchemy:
                ticker = uow_sqlalchemy.sec_filings.get_ticker_by_cik(filing_data['cik'])

        print(f"🔄 Processing 10-K filing for ticker: {ticker}")

        if not ticker:
            print(f"⚠️  No ticker found for CIK: {filing_data['cik']}")
            return

        # Process the filing
        result = service.get_consolidated_income_statements(
            ticker=ticker,
            uow_instance=uow_instance,
            form_type="10-K",
            retrieve_from_database=False,
            overwrite_database=True
        )

        print(f"✅ Successfully processed 10-K for {ticker}")
        print(f"   Statements count: {len(result.statements) if result.statements else 0}")

    except Exception as e:
        print(f"❌ Error processing 10-K filing: {e}")

async def send_ping(websocket):
    while True:
        try:
            pong_waiter = await websocket.ping()
            await asyncio.wait_for(pong_waiter, timeout=5)
            await asyncio.sleep(30)
        except Exception as e:
            print(f"An error occurred while sending ping: {e}")
            await websocket.close()
            return

async def websocket_client():
    retry_counter = 0
    max_retries = 5
    ping_task = None
    background_tasks = set()  # Keep track of background tasks

    while retry_counter < max_retries:
        try:
            async with websockets.connect(WS_ENDPOINT) as websocket:
                print("✅ Connected to:", SERVER_URL)
                retry_counter = 0

                # Start the ping/pong keep-alive routine
                ping_task = asyncio.create_task(send_ping(websocket))

                # Start the message-receiving loop
                while True:
                    message = await websocket.recv()
                    filings = json.loads(message)

                    for filing in filings:
                        print(f"📄 {filing['accessionNo']} {filing['formType']} {filing['filedAt']} CIK:{filing['cik']}")

                        # Only process 10-K filings
                        if filing['formType'] == '10-K':
                            print(f"🎯 Found 10-K filing! Starting background processing...")

                            # Create background task for processing
                            task = asyncio.create_task(process_10k_filing(filing))
                            background_tasks.add(task)

                            # Clean up completed tasks to prevent memory leaks
                            task.add_done_callback(background_tasks.discard)

        except Exception as e:
            retry_counter += 1
            print(f"Connection closed with message: {e}")
            print(f"Reconnecting in 5 sec... (Attempt {retry_counter}/{max_retries})")

            # Cancel the ping task
            if ping_task is not None:
                try:
                    ping_task.cancel()
                    await ping_task
                except Exception:
                    pass
                ping_task = None

            # Wait for background tasks to complete (optional)
            if background_tasks:
                print(f"⏳ Waiting for {len(background_tasks)} background tasks to complete...")
                await asyncio.gather(*background_tasks, return_exceptions=True)
                background_tasks.clear()

            await asyncio.sleep(5)

    print("Maximum reconnection attempts reached. Stopping client.")


if __name__ == "__main__":
    asyncio.run(websocket_client())
