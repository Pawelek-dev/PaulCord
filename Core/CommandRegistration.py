import aiohttp
import asyncio
import random
from typing import Any, Dict, List, Tuple
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

class SlashCommand:
    def __init__(
        self,
        name: str,
        description: str,
        options: List[Dict[str, Any]] = None,
        integration_types: bool = False,
        version: int = 1
    ):
        self.name = name
        self.description = description
        self.options = options or []
        self.integration_types = integration_types
        self.version = version

class CommandRegistration:
    def __init__(self, client) -> None:
        self.client = client
        self.console = Console()

    async def rate_limit_sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)

    async def send_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        json: Any = None
    ) -> Tuple[int, Any]:
        max_attempts = 5
        attempts = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
            refresh_per_second=5
        ) as progress:
            task_id = progress.add_task(
                f"[cyan]Sending request: {method} {url} (attempt {attempts+1}/{max_attempts})[/cyan]",
                total=None
            )

            while attempts < max_attempts:
                progress.update(
                    task_id,
                    description=(
                        f"[cyan]Request: {method} {url} "
                        f"(attempt {attempts+1}/{max_attempts})[/cyan]"
                    )
                )

                async with self.client.session.request(
                    method, url, headers=headers, json=json
                ) as response:
                    status_code = response.status
                    response_text = await response.text()

                    progress.update(
                        task_id,
                        description=(
                            f"[yellow]Status Code: {status_code}. "
                            f"Processing response...[/yellow]"
                        )
                    )

                    if status_code == 429:
                        data = await response.json()
                        retry_after = data.get('retry_after', 1)
                        progress.update(
                            task_id,
                            description=(
                                f"[bold red]Rate limited! Sleeping for {retry_after}s. "
                                f"Attempt {attempts+1}/{max_attempts}[/bold red]"
                            )
                        )
                        await self.rate_limit_sleep(retry_after)
                        attempts += 1
                        continue

                    if response.content_type == 'application/json':
                        json_data = await response.json()
                        return status_code, json_data
                    else:
                        return status_code, response_text

            raise Exception(f"Max attempts reached for {method} {url}")

    async def get_existing_commands(self) -> List[Dict[str, Any]]:
        url = f"{self.client.base_url}/applications/{self.client.application_id}/commands"
        headers = {
            "Authorization": f"Bot {self.client.token}"
        }

        status_code, response_data = await self.send_request("GET", url, headers)
        if status_code == 200:
            return response_data
        else:
            self.console.print("[red]Failed to retrieve existing commands.[/red]")
            return []

    def commands_are_equal(
        self,
        existing_command: Dict[str, Any],
        new_command: Dict[str, Any]
    ) -> bool:
        return (
            existing_command['name'] == new_command['name'] and
            existing_command['description'] == new_command['description'] and
            existing_command.get('options', []) == new_command.get('options', []) and
            existing_command.get('integration_types', []) == new_command.get('integration_types', []) and
            existing_command.get('version', 1) == new_command.get('version', 1)
        )

    async def register_commands(self) -> None:
        url = f"{self.client.base_url}/applications/{self.client.application_id}/commands"
        headers = {
            "Authorization": f"Bot {self.client.token}",
            "Content-Type": "application/json"
        }

        existing_commands = await self.get_existing_commands()

        for command in self.client.commands:
            payload = {
                "name": command["name"],
                "description": command["description"],
                "options": self.build_options(command.get("options", [])),
                "contexts": [0, 1, 2],
                "integration_types": (
                    [0, 1] if command.get("integration_types", False) else [0]
                )
            }

            existing_command = next(
                (cmd for cmd in existing_commands if cmd['name'] == command["name"]),
                None
            )

            if existing_command and self.commands_are_equal(existing_command, command):
                self.console.print(
                    f"[green]Command '{command['name']}' is already up to date. "
                    "Skipping registration.[/green]"
                )
                continue

            if existing_command:
                self.console.print(
                    f"[cyan]Updating command: {command['name']}[/cyan]"
                )
            else:
                self.console.print(
                    f"[cyan]Registering new command: {command['name']}[/cyan]"
                )

            status_code, response_data = await self.send_request("POST", url, headers, json=payload)

            if status_code not in [200, 201]:
                self.console.print(
                    f"[red]Failed to register/update command '{command['name']}': "
                    f"{status_code} {response_data}[/red]"
                )
            else:
                if existing_command:
                    self.console.print(
                        f"[green]Command '{command['name']}' updated successfully.[/green]"
                    )
                else:
                    self.console.print(
                        f"[green]Command '{command['name']}' registered successfully.[/green]"
                    )

    async def delete_command(self, command_id: str) -> None:
        url = f"{self.client.base_url}/applications/{self.client.application_id}/commands/{command_id}"
        headers = {
            "Authorization": f"Bot {self.client.token}"
        }

        status_code, response_data = await self.send_request("DELETE", url, headers)
        if status_code == 204:
            self.console.print(
                f"[green]Command {command_id} deleted successfully.[/green]"
            )
        else:
            self.console.print(
                f"[red]Failed to delete command {command_id}: {status_code} {response_data}[/red]"
            )

    async def sync_commands(self) -> None:
        existing_commands = await self.get_existing_commands()
        existing_commands_dict = {cmd['name']: cmd for cmd in existing_commands}

        for command in self.client.commands:
            command_payload = {
                "name": command["name"],
                "description": command["description"],
                "options": self.build_options(command.get("options", [])),
                "integration_types": (
                    [0, 1] if command.get("integration_types", False) else [0]
                ),
                "contexts": [0, 1, 2]
            }

            if command["name"] in existing_commands_dict:
                existing_command = existing_commands_dict[command["name"]]
                if self.commands_are_equal(existing_command, command):
                    continue

                self.console.print(
                    f"[cyan]Updating command: {command['name']}[/cyan]"
                )
                status_code, response_data = await self.send_request(
                    "POST",
                    f"{self.client.base_url}/applications/{self.client.application_id}/commands",
                    {"Authorization": f"Bot {self.client.token}", "Content-Type": "application/json"},
                    json=command_payload
                )

                if status_code in [200, 201]:
                    self.console.print(
                        f"[green]Command '{command['name']}' updated successfully.[/green]"
                    )
                else:
                    self.console.print(
                        f"[red]Failed to update command '{command['name']}': {status_code} {response_data}[/red]"
                    )
            else:
                self.console.print(
                    f"[cyan]Registering new command: {command['name']}[/cyan]"
                )
                status_code, response_data = await self.send_request(
                    "POST",
                    f"{self.client.base_url}/applications/{self.client.application_id}/commands",
                    {"Authorization": f"Bot {self.client.token}", "Content-Type": "application/json"},
                    json=command_payload
                )
                if status_code in [200, 201]:
                    self.console.print(
                        f"[green]Command '{command['name']}' registered successfully.[/green]"
                    )
                else:
                    self.console.print(
                        f"[red]Failed to register command '{command['name']}': {status_code} {response_data}[/red]"
                    )

        for existing_command in existing_commands:
            if existing_command["name"] not in {cmd["name"] for cmd in self.client.commands}:
                self.console.print(
                    f"[magenta]Deleting command: {existing_command['name']}[/magenta]"
                )
                await self.delete_command(existing_command['id'])

    def build_options(self, options: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        discord_options = []
        for option in options:
            discord_option = {
                "type": option["type"],
                "name": option["name"],
                "description": option["description"],
                "required": option.get("required", False)
            }
            discord_options.append(discord_option)
        return discord_options
