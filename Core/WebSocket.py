import asyncio
import json
import aiohttp
import time
import signal
import logging


class WebSocketManager:
    def __init__(self, client, shard_id=0, total_shards=1):
        self.client = client
        self.shard_id = shard_id
        self.total_shards = total_shards
        self.last_ping = None
        self.ping_timestamp = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_interval = 5
        self.max_heartbeat_failures = 5
        self.failed_heartbeats = 0
        self.session = None
        self.logger = logging.getLogger(f"WebSocketManager_{shard_id}")
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler(f"websocket_shard_{shard_id}.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        # Rejestracja obsługi sygnałów systemowych
        signal.signal(signal.SIGINT, self.graceful_shutdown)
        signal.signal(signal.SIGTERM, self.graceful_shutdown)

    async def init_session(self):
        self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session:
            await self.session.close()

    async def heartbeat(self):
        while self.client.running:
            if self.client.heartbeat_interval is None:
                await asyncio.sleep(5)
                continue

            current_time = time.time()
            if self.ping_timestamp and (current_time - self.ping_timestamp) < (self.client.heartbeat_interval / 1000):
                await asyncio.sleep(1)
                continue

            self.client.ping_timestamp = current_time

            if not self.client.last_heartbeat_ack:
                self.failed_heartbeats += 1
                self.logger.warning(f"Shard {self.shard_id}: Heartbeat timeout ({self.failed_heartbeats}/{self.max_heartbeat_failures}). Reconnecting...")

                if self.failed_heartbeats >= self.max_heartbeat_failures:
                    if self.client.ws:
                        try:
                            await self.client.ws.close()
                        except Exception as e:
                            self.logger.error(f"Shard {self.shard_id}: Error closing WebSocket connection: {e}")
                    break

            self.failed_heartbeats = 0
            self.client.last_heartbeat_ack = False
            self.ping_timestamp = current_time

            payload = {
                "op": 1,
                "d": self.client.sequence if self.client.sequence is not None else 0
            }

            if self.client.ws:
                try:
                    await self.client.ws.send_json(payload)
                    self.logger.info(f"Shard {self.shard_id}: Sending heartbeat with sequence: {self.client.sequence}")

                    await asyncio.sleep(self.client.heartbeat_interval / 1000)
                    if self.client.last_heartbeat_ack:
                        self.client.last_ping = (time.time() - self.client.ping_timestamp) * 1000  # ms

                except Exception as e:
                    self.logger.error(f"Shard {self.shard_id}: Error sending heartbeat: {e}")
                    break


    async def connect(self):
        if self.session is None:
            await self.init_session()

        while self.client.running and (self.reconnect_attempts < self.max_reconnect_attempts or self.max_reconnect_attempts is None):
            try:
                async with self.session.ws_connect(self.client.gateway_url) as ws:
                    self.client.ws = ws
                    self.reconnect_attempts = 0
                    await self.identify()
                    asyncio.create_task(self.heartbeat())
                    self.logger.info("WebSocket connected.")
                    await self.listen()

            except aiohttp.ClientConnectionError as e:
                self.reconnect_attempts += 1
                retry_delay = min(self.reconnect_interval * (2 ** (self.reconnect_attempts - 1)), 60)
                self.logger.warning(f"WebSocket connection error: {e}. Attempting reconnect ({self.reconnect_attempts}/{self.max_reconnect_attempts}) in {retry_delay} seconds.")
                await asyncio.sleep(retry_delay)

            except asyncio.TimeoutError as e:
                self.logger.error(f"WebSocket connection timed out: {e}")
                await asyncio.sleep(5)

            except ConnectionResetError as e:
                self.logger.error(f"WebSocket connection reset: {e}")
                await asyncio.sleep(5)

            except Exception as e:
                self.logger.error(f"Unexpected error during WebSocket connection: {e}")
                await asyncio.sleep(5)

    async def identify(self):
        payload = {
            "op": 2,
            "d": {
                "token": self.client.token,
                "intents": self.client.intents.value,
                "properties": {
                    "$os": "linux",
                    "$browser": "PaulCLIClient",
                    "$device": "PaulCLIClient"
                },
                "shard": [self.shard_id, self.total_shards]
            }
        }
        self.logger.info(f"Shard {self.shard_id}: Sending identify payload")
        if self.client.ws:
            try:
                await self.client.ws.send_json(payload)
            except Exception as e:
                self.logger.error(f"Shard {self.shard_id}: Error sending identify payload: {e}")

    async def listen(self):
        async for msg in self.client.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = msg.json()
                    self.logger.info(f"Received WebSocket message: {data}")

                    if 'd' in data and data.get('t') == 'INTERACTION_CREATE':
                        await self.client.interaction_handler.handle_interaction(data['d'])
                    else:
                        self.logger.debug(f"Skipping non-interaction message: {data}")

                except Exception as e:
                    self.logger.error(f"Error while processing WebSocket message: {e}")
            elif msg.type == aiohttp.WSMsgType.BINARY:
                self.logger.info("Received binary WebSocket message.")
            elif msg.type == aiohttp.WSMsgType.PING:
                self.logger.info("Received WebSocket ping.")
            elif msg.type == aiohttp.WSMsgType.PONG:
                self.logger.info("Received WebSocket pong.")
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                self.logger.info("WebSocket closed.")
                break
            elif msg.type == aiohttp.WSMsgType.ERROR:
                self.logger.error(f"WebSocket error: {msg.data}")
                break

    def graceful_shutdown(self, signum, frame):
        self.logger.info("Received shutdown signal. Closing WebSocket connection gracefully.")
        self.client.running = False
        if self.client.ws:
            asyncio.create_task(self.client.ws.close())
