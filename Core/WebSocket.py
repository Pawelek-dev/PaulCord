import asyncio
import aiohttp
import time
import signal
import logging
import random
import sys
from typing import Optional
import json

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn


def truncate_json(data: dict, max_length: int = 300) -> str:
    raw_str = json.dumps(data, indent=2, ensure_ascii=False)
    if len(raw_str) > max_length:
        return raw_str[:max_length] + "... (truncated)"
    return raw_str


class WebSocketManager:
    def __init__(self, client, shard_id: int = 0, total_shards: int = 1) -> None:
        self.client = client
        self.shard_id = shard_id
        self.total_shards = total_shards
        self.last_ping: Optional[float] = None
        self.ping_timestamp: Optional[float] = None
        self.reconnect_attempts: int = 0
        self.max_reconnect_attempts: Optional[int] = 5
        self.reconnect_interval: int = 5
        self.max_heartbeat_failures: int = 5
        self.failed_heartbeats: int = 0
        self.session: Optional[aiohttp.ClientSession] = None
        self.heartbeat_task: Optional[asyncio.Task] = None

        self.logger = logging.getLogger(f"WebSocketManager_{shard_id}")
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler(f"websocket_shard_{shard_id}.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.console = Console()

        self.progress: Optional[Progress] = None
        self.progress_task_id: Optional[int] = None

        try:
            loop = asyncio.get_event_loop()
            if sys.platform != "win32":
                loop.add_signal_handler(signal.SIGINT, self.graceful_shutdown, signal.SIGINT, None)
                loop.add_signal_handler(signal.SIGTERM, self.graceful_shutdown, signal.SIGTERM, None)
            else:
                signal.signal(signal.SIGINT, self.graceful_shutdown)
                signal.signal(signal.SIGTERM, self.graceful_shutdown)
        except Exception as e:
            self.logger.error(f"Error setting up signal handlers: {e}")

    async def init_session(self) -> None:
        self.session = aiohttp.ClientSession()

    async def close(self) -> None:
        if self.session:
            await self.session.close()

    async def heartbeat(self) -> None:
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
                if self.progress:
                    self.progress.console.log(
                        f"[yellow]Shard {self.shard_id}: Heartbeat timeout "
                        f"({self.failed_heartbeats}/{self.max_heartbeat_failures}). Reconnecting...[/yellow]"
                    )

                self.logger.warning(
                    f"Shard {self.shard_id}: Heartbeat timeout "
                    f"({self.failed_heartbeats}/{self.max_heartbeat_failures})."
                )

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
                    if self.progress:
                        self.progress.console.log(
                            f"[cyan]Shard {self.shard_id}: Sending heartbeat with sequence: {self.client.sequence}[/cyan]"
                        )
                    await asyncio.sleep(self.client.heartbeat_interval / 1000)
                    if self.client.last_heartbeat_ack:
                        self.client.last_ping = (time.time() - self.client.ping_timestamp) * 1000
                except Exception as e:
                    self.logger.error(f"Shard {self.shard_id}: Error sending heartbeat: {e}")
                    break

    async def connect(self) -> None:
        if self.session is None:
            await self.init_session()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=False,
            refresh_per_second=5
        ) as progress:
            self.progress = progress
            self.progress_task_id = progress.add_task(
                f"Shard {self.shard_id} - Listening for WebSocket messages",
                total=None
            )

            while self.client.running and (
                self.reconnect_attempts < self.max_reconnect_attempts
                or self.max_reconnect_attempts is None
            ):
                try:
                    async with self.session.ws_connect(self.client.gateway_url) as ws:
                        self.client.ws = ws
                        self.reconnect_attempts = 0
                        await self.identify()

                        self.heartbeat_task = asyncio.create_task(self.heartbeat())

                        progress.update(
                            self.progress_task_id,
                            description=f"Shard {self.shard_id}: Connected. Listening..."
                        )

                        await self.listen()

                        if self.heartbeat_task and not self.heartbeat_task.done():
                            self.heartbeat_task.cancel()
                            try:
                                await self.heartbeat_task
                            except asyncio.CancelledError:
                                pass

                except aiohttp.ClientConnectionError as e:
                    self.reconnect_attempts += 1
                    retry_delay = min(self.reconnect_interval * (2 ** (self.reconnect_attempts - 1)), 60)
                    progress.console.log(
                        f"[yellow]WebSocket connection error: {e}. "
                        f"Attempting reconnect ({self.reconnect_attempts}/{self.max_reconnect_attempts}) "
                        f"in {retry_delay} seconds.[/yellow]"
                    )
                    await asyncio.sleep(retry_delay + random.uniform(0, 2))
                except asyncio.TimeoutError as e:
                    self.logger.error(f"WebSocket connection timed out: {e}")
                    await asyncio.sleep(5)
                except ConnectionResetError as e:
                    self.logger.error(f"WebSocket connection reset: {e}")
                    await asyncio.sleep(5)
                except Exception as e:
                    self.logger.error(f"Unexpected error during WebSocket connection: {e}")
                    await asyncio.sleep(5)

            progress.stop()

    async def identify(self) -> None:
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
        if self.progress:
            self.progress.console.log(
                f"[cyan]Shard {self.shard_id}: Sending identify payload (token hidden)[/cyan]"
            )
        try:
            if self.client.ws:
                await self.client.ws.send_json(payload)
        except Exception as e:
            self.logger.error(f"Shard {self.shard_id}: Error sending identify payload: {e}")

    async def handle_text_message(self, msg: aiohttp.WSMessage) -> None:
        try:
            data = msg.json()
            truncated_data = truncate_json(data, max_length=200)

            if self.progress and self.progress_task_id is not None:
                self.progress.update(self.progress_task_id, advance=1)
                self.progress.console.log(f"[cyan]Received WebSocket message: {truncated_data}[/cyan]")

            if 'd' in data and data.get('t') == 'INTERACTION_CREATE':
                await self.client.interaction_handler.handle_interaction(data['d'])
            else:
                event_type = data.get('t')
                if self.progress:
                    self.progress.console.log(f"[dim]Skipping non-interaction message. Event: {event_type}[/dim]")
        except Exception as e:
            self.logger.error(f"Error while processing WebSocket text message: {e}")

    async def listen(self) -> None:
        if not self.client.ws:
            return

        async for msg in self.client.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                await self.handle_text_message(msg)
            elif msg.type == aiohttp.WSMsgType.BINARY:
                if self.progress:
                    self.progress.console.log("[cyan]Received binary WebSocket message.[/cyan]")
            elif msg.type == aiohttp.WSMsgType.PING:
                if self.progress:
                    self.progress.console.log("[cyan]Received WebSocket ping.[/cyan]")
            elif msg.type == aiohttp.WSMsgType.PONG:
                if self.progress:
                    self.progress.console.log("[cyan]Received WebSocket pong.[/cyan]")
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                if self.progress:
                    self.progress.console.log("[cyan]WebSocket closed.[/cyan]")
                break
            elif msg.type == aiohttp.WSMsgType.ERROR:
                self.logger.error(f"WebSocket error: {msg.data}")
                break

    def graceful_shutdown(self, signum, frame) -> None:
        if self.progress:
            self.progress.console.log("[cyan]Received shutdown signal. Closing WebSocket connection gracefully.[/cyan]")
        self.client.running = False
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
        if self.client.ws:
            asyncio.create_task(self.client.ws.close())
