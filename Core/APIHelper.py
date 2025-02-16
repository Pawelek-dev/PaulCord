import aiohttp
import logging
from typing import Optional, Dict, Any
from rich.console import Console

class APIHelper:
    def __init__(self, client):
        self.client = client
        self.logger = logging.getLogger("APIHelper")
        self.console = Console()

    async def send_interaction_response(
        self,
        interaction_id: str,
        interaction_token: str,
        message: Optional[str] = None,
        embed: Optional[Dict[str, Any]] = None,
        ephemeral: bool = False,
        components: Optional[Any] = None
    ) -> None:
        
        url = f"https://discord.com/api/v10/interactions/{interaction_id}/{interaction_token}/callback"
        json_data = {"type": 4, "data": {}}
        if message:
            json_data["data"]["content"] = message
        if ephemeral:
            json_data["data"]["flags"] = 64
        if embed:
            json_data["data"]["embeds"] = [embed]
        if components:
            json_data["data"]["components"] = components

        self.logger.info(f"Sending interaction response: {json_data}")

        session_provided = hasattr(self.client, "session") and self.client.session is not None
        session = self.client.session if session_provided else aiohttp.ClientSession()

        try:
            async with session.post(url, json=json_data) as response:
                if 200 <= response.status < 300:
                    self.console.print(f"[green]Interaction response sent successfully for interaction {interaction_id}[/green]")
                else:
                    text = await response.text()
                    self.logger.error(f"Failed to send interaction response: {response.status} {text}")
                    self.console.print(f"[red]Failed to send interaction response: {response.status} {text}[/red]")
        except Exception as e:
            self.logger.exception(f"Exception while sending interaction response: {e}")
            self.console.print(f"[red]Exception while sending interaction response: {e}[/red]")
        finally:
            if not session_provided:
                await session.close()
