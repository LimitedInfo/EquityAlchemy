import asyncio
import websockets
import json
import os
import sys
import signal
import time
import traceback
import aiohttp
from aiohttp import web

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from service_layer import service, uow

API_KEY = os.getenv("SEC_API_KEY")
SERVER_URL = "wss://stream.sec-api.io"
WS_ENDPOINT = SERVER_URL + "?apiKey=" + API_KEY

print("🚀 Filing Listener Starting...")
print(f"📡 Server URL: {SERVER_URL}")
print(f"🔑 API Key Present: {'Yes' if API_KEY else 'No'}")
if API_KEY:
    print(f"🔑 API Key (first 10 chars): {API_KEY[:10]}...")
else:
    print("❌ SEC_API_KEY environment variable is not set!")
    sys.exit(1)

print(f"🌐 WebSocket Endpoint: {WS_ENDPOINT}")
print("🔄 Attempting to connect...")

shutdown_event = asyncio.Event()
start_time = time.time()
message_count = 0
last_message_time = time.time()

async def health_check(request):
    """HTTP health check endpoint for Fly.io"""
    try:
        uptime = time.time() - start_time
        time_since_last_message = time.time() - last_message_time

        # Consider unhealthy if no messages in 10 minutes (but only after initial startup)
        is_healthy = True
        if uptime > 120 and time_since_last_message > 600:  # 2 min startup grace, then 10 min message timeout
            is_healthy = False

        status = {
            "status": "healthy" if is_healthy else "warning",
            "uptime_seconds": round(uptime, 1),
            "messages_processed": message_count,
            "seconds_since_last_message": round(time_since_last_message, 1),
            "websocket_connected": not shutdown_event.is_set(),
            "timestamp": time.time(),
            "start_time": start_time,
            "last_message_time": last_message_time,
            "is_healthy": is_healthy
        }

        # Always log health check requests for debugging
        print(f"🏥 Health check: status={status['status']}, uptime={status['uptime_seconds']}s, messages={status['messages_processed']}, last_msg={status['seconds_since_last_message']}s ago")

        # Return appropriate status code
        status_code = 200 if is_healthy else 503
        return web.json_response(status, status=status_code)

    except Exception as e:
        print(f"❌ Error in health_check: {e}")
        print(f"❌ Health check traceback: {traceback.format_exc()}")
        error_status = {
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }
        return web.json_response(error_status, status=500)

async def ping(request):
    """Simple ping endpoint for testing"""
    return web.json_response({"ping": "pong", "timestamp": time.time()})

async def start_health_server():
    """Start HTTP health check server"""
    try:
        app = web.Application()
        app.router.add_get('/', health_check)
        app.router.add_get('/health', health_check)
        app.router.add_get('/ping', ping)

        # Add middleware to log all requests
        async def log_middleware(app, handler):
            async def middleware_handler(request):
                print(f"🌐 Health request: {request.method} {request.path} from {request.remote}")
                response = await handler(request)
                print(f"🌐 Health response: {response.status}")
                return response
            return middleware_handler

        app.middlewares.append(log_middleware)

        runner = web.AppRunner(app)
        await runner.setup()

        # Explicitly bind to all interfaces
        site = web.TCPSite(runner, host='0.0.0.0', port=8080, reuse_address=True, reuse_port=True)
        await site.start()

        print("🏥 Health check server started successfully")
        print("🏥 Listening on: 0.0.0.0:8080")
        print("🏥 Health endpoints:")
        print("   - GET /")
        print("   - GET /health")

        # List all sites to confirm binding
        for site in runner.sites:
            print(f"🏥 Site: {site.name}")

        return runner
    except Exception as e:
        print(f"❌ Failed to start health server: {e}")
        print(f"❌ Health server error traceback: {traceback.format_exc()}")
        raise

async def process_10k_filing(filing_data):
    """Process a 10-K filing in the background"""
    time.sleep(1.2)
    print("waiting 1.2 seconds for the filing to be available")
    try:
        uow_instance = uow.SqlAlchemyUnitOfWork()

        with uow_instance as uow_sqlalchemy:
            ticker = uow_sqlalchemy.sec_filings.get_ticker_by_cik(filing_data['cik'])

        print(f"🔄 Processing 10-K filing for ticker: {ticker}")

        if not ticker:
            print(f"⚠️  No ticker found for CIK: {filing_data['cik']}")
            return

        result = service.get_consolidated_income_statements(
            ticker=ticker,
            uow_instance=uow_instance,
            form_type="10-K",
            retrieve_from_database=False,
            overwrite_database=True
        )

        print(f"✅ Successfully processed 10-K for {ticker}")

    except Exception as e:
        print(f"❌ Error processing 10-K filing: {e}")

async def send_ping(websocket):
    ping_count = 0
    while not shutdown_event.is_set():
        try:
            ping_count += 1
            print(f"🏓 Sending ping #{ping_count}")
            pong_waiter = await websocket.ping()
            await asyncio.wait_for(pong_waiter, timeout=5)
            print(f"🏓 Pong received #{ping_count}")
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            print(f"🔄 Ping task cancelled after {ping_count} pings")
            break
        except Exception as e:
            print(f"❌ Error in ping task: {e}")
            break

async def health_monitor():
    """Monitor the health of the application"""
    while not shutdown_event.is_set():
        try:
            uptime = time.time() - start_time
            print(f"💚 Health check: Uptime {uptime:.1f}s, Messages: {message_count}, Shutdown event: {shutdown_event.is_set()}")
            await asyncio.sleep(60)  # Health check every minute
        except asyncio.CancelledError:
            print("🔄 Health monitor cancelled")
            break
        except Exception as e:
            print(f"❌ Error in health monitor: {e}")
            break

async def websocket_client():
    global message_count, last_message_time
    retry_counter = 0
    max_retries = 5
    ping_task = None
    health_task = None
    background_tasks = set()

    print(f"🔄 Starting WebSocket client (max retries: {max_retries})...")

    while retry_counter < max_retries and not shutdown_event.is_set():
        try:
            print(f"🔌 Attempting connection to {WS_ENDPOINT}")

            if shutdown_event.is_set():
                print("🛑 Shutdown event detected before connection attempt")
                break

            async with websockets.connect(WS_ENDPOINT) as websocket:
                print("✅ Connected to:", SERVER_URL)
                print("🎧 Listening for SEC filings...")
                retry_counter = 0

                ping_task = asyncio.create_task(send_ping(websocket))
                health_task = asyncio.create_task(health_monitor())

                while not shutdown_event.is_set():
                    try:
                        print(f"🔄 Waiting for message... (shutdown_event: {shutdown_event.is_set()})")
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        message_count += 1
                        last_message_time = time.time()

                        if shutdown_event.is_set():
                            print(f"🛑 Shutdown event detected after receiving message {message_count}")
                            break

                        filings = json.loads(message)

                        for filing in filings:
                            print(f"📄 {filing['accessionNo']} {filing['formType']} {filing['filedAt']} CIK:{filing['cik']}")

                            if filing['formType'] == '10-K':
                                print(f"🎯 Found 10-K filing! Starting background processing...")

                                task = asyncio.create_task(process_10k_filing(filing))
                                background_tasks.add(task)
                                task.add_done_callback(background_tasks.discard)

                        if shutdown_event.is_set():
                            print(f"🛑 Shutdown event detected after processing {len(filings)} filings")
                            break

                    except asyncio.TimeoutError:
                        if shutdown_event.is_set():
                            print("🛑 Shutdown event detected during timeout")
                            break
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        print("🔗 WebSocket connection closed by server")
                        break
                    except Exception as e:
                        print(f"❌ Exception in message loop: {e}")
                        print(f"❌ Exception traceback: {traceback.format_exc()}")
                        break

                print(f"🔄 Exiting WebSocket loop (shutdown_event: {shutdown_event.is_set()})")
                break

        except websockets.exceptions.InvalidStatusCode as e:
            if shutdown_event.is_set():
                print(f"🛑 Shutdown event detected during connection error: {e.status_code}")
                break
            retry_counter += 1
            print(f"❌ WebSocket connection failed with status code: {e.status_code}")
            print(f"🔄 Reconnecting in 5 sec... (Attempt {retry_counter}/{max_retries})")
        except websockets.exceptions.ConnectionClosed as e:
            if shutdown_event.is_set():
                print(f"🛑 Shutdown event detected during connection closed: {e}")
                break
            retry_counter += 1
            print(f"❌ WebSocket connection closed: {e}")
            print(f"🔄 Reconnecting in 5 sec... (Attempt {retry_counter}/{max_retries})")
        except Exception as e:
            if shutdown_event.is_set():
                print(f"🛑 Shutdown event detected during exception: {e}")
                break
            retry_counter += 1
            print(f"❌ Connection error: {e}")
            print(f"   Error type: {type(e).__name__}")
            print(f"   Error traceback: {traceback.format_exc()}")
            print(f"🔄 Reconnecting in 5 sec... (Attempt {retry_counter}/{max_retries})")

            if not shutdown_event.is_set():
                await asyncio.sleep(5)

    print(f"🔄 Cleaning up tasks...")

    if ping_task is not None:
        print(f"🔄 Cancelling ping task")
        ping_task.cancel()
        try:
            await ping_task
        except asyncio.CancelledError:
            print("🔄 Ping task cleanup completed")

    if health_task is not None:
        print(f"🔄 Cancelling health task")
        health_task.cancel()
        try:
            await health_task
        except asyncio.CancelledError:
            print("🔄 Health task cleanup completed")

    if background_tasks:
        print(f"⏳ Waiting for {len(background_tasks)} background tasks to complete...")
        try:
            await asyncio.gather(*background_tasks, return_exceptions=True)
        except Exception as e:
            print(f"⚠️ Error during background task cleanup: {e}")

    if shutdown_event.is_set():
        print("🛑 Graceful shutdown completed")
    else:
        print("❌ Maximum reconnection attempts reached. Stopping client.")

def signal_handler():
    print(f"🛑 SIGNAL HANDLER CALLED!")
    print(f"🛑 Current time: {time.time()}")
    print(f"🛑 Uptime: {time.time() - start_time:.1f}s")
    print(f"🛑 Messages processed: {message_count}")
    print(f"🛑 Stack trace:")
    traceback.print_stack()
    print(f"🛑 Setting shutdown event...")
    shutdown_event.set()
    print(f"🛑 Shutdown event set: {shutdown_event.is_set()}")

async def main():
    print(f"🔄 Starting main function...")

    health_server = None

    try:
        # Start health check server first - this is critical
        print("🔄 Starting health check server...")
        try:
            health_server = await start_health_server()

            # Give the server a moment to fully start
            await asyncio.sleep(1.0)

            # Verify the server is actually running by making a test request
            print("🔄 Verifying health server is accessible...")
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get('http://localhost:8080/health', timeout=5) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            print(f"✅ Health server verified: {data}")
                        else:
                            print(f"❌ Health server returned unexpected status: {resp.status}")
                            raise Exception(f"Health server not responding correctly: {resp.status}")
                except asyncio.TimeoutError:
                    print("❌ Health server verification timed out")
                    raise Exception("Health server not accessible")
                except Exception as e:
                    print(f"❌ Health server verification failed: {e}")
                    raise

        except Exception as e:
            print(f"❌ CRITICAL: Failed to start health server: {e}")
            print(f"❌ Health server traceback: {traceback.format_exc()}")
            # Cannot continue without health server on Fly.io
            sys.exit(1)

        loop = asyncio.get_running_loop()

        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, signal_handler)
            print("🔧 Signal handlers registered")
        except NotImplementedError:
            print("⚠️ Signal handlers not available on this platform")

        print(f"🔄 About to start websocket client...")
        await websocket_client()
        print(f"🔄 Websocket client returned...")

    except asyncio.CancelledError:
        print("🔄 Main task cancelled")
    except Exception as e:
        print(f"❌ Unexpected error in main: {e}")
        print(f"❌ Main error traceback: {traceback.format_exc()}")
        shutdown_event.set()
    finally:
        # Clean up health server
        if health_server:
            try:
                await health_server.cleanup()
                print("🏥 Health server shutdown")
            except Exception as e:
                print(f"⚠️ Error during health server cleanup: {e}")

if __name__ == "__main__":
    try:
        print(f"🔄 Running main...")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Received KeyboardInterrupt in main")
    except Exception as e:
        print(f"❌ Unexpected error in main runner: {e}")
        print(f"❌ Main runner traceback: {traceback.format_exc()}")
        sys.exit(1)
    finally:
        print("🏁 Filing listener shutdown complete")
