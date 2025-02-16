from rich.console import Console

class InteractionHandler:
    def __init__(self, client):
        self.client = client
        self.console = Console()

    async def send_interaction_response(self, interaction_id, interaction_token, message=None, embed=None, ephemeral=False, components=None):
        await self.client.api_helper.send_interaction_response(interaction_id, interaction_token, message, embed, ephemeral, components)

    async def handle_command(self, interaction):
        command_name = interaction['data']['name']
        command = next((cmd for cmd in self.client.commands if cmd['name'] == command_name), None)
        if command:
            try:
                await command['func'](self.client, interaction)
                self.console.print(f"[green]Received slash command: {command_name}[/green]")
            except Exception as e:
                self.console.print(f"[red]Error executing command: {command_name}[/red]")
                self.client.logger.error(f"Error executing command {command_name}: {e}")
        else:
            self.console.print(f"[red]Unknown command: {command_name}[/red]")

    async def handle_component(self, interaction):
        custom_id = interaction['data'].get('custom_id', '')
        handler = self.client.component_handlers.get(custom_id)
        if handler:
            try:
                await handler(self.client, interaction)
            except Exception as e:
                self.console.print(f"[red]Error handling component with custom_id: {custom_id}[/red]")
                self.client.logger.error(f"Error while handling component {custom_id}: {e}")
        else:
            self.console.print(f"[red]No handler found for component with custom_id: {custom_id}[/red]")

    async def handle_interaction(self, interaction):
        self.console.print(f"[cyan]Handling interaction: {interaction.get('type', 'N/A')}[/cyan]")
        interaction_type = interaction.get('type')

        if not interaction_type:
            self.console.print("[red]Interaction type missing in payload.[/red]")
            return

        if interaction_type == 2:
            command_name = interaction['data']['name']
            self.console.print(f"[cyan]Received slash command: {command_name}[/cyan]")
            command = next((cmd for cmd in self.client.commands if cmd['name'] == command_name), None)

            if command:
                try:
                    self.console.print(f"[cyan]Executing command: {command_name}[/cyan]")
                    result_message = await command['func'](self.client, interaction)
                    if result_message:
                        await self.client.api_helper.send_interaction_response(
                            interaction["id"],
                            interaction["token"],
                            message=result_message
                        )
                    else:
                        self.console.print(f"[yellow]No response message for command {command_name}, skipping send.[/yellow]")
                except Exception as e:
                    self.console.print(f"[red]Error while executing command {command_name}[/red]")
                    self.client.logger.error(f"Error while executing command {command_name}: {e}")
                    await self.client.api_helper.send_interaction_response(
                        interaction["id"],
                        interaction["token"],
                        message=f"An error occurred while executing the command. \n`{e}`"
                    )
            else:
                self.console.print(f"[red]Unknown command: {command_name}[/red]")
                await self.client.api_helper.send_interaction_response(
                    interaction["id"], interaction["token"], message="Unknown command"
                )

        elif interaction_type == 3:
            custom_id = interaction['data'].get('custom_id', '')
            handler = self.client.component_handlers.get(custom_id)
            if handler:
                try:
                    await handler(self.client, interaction)
                except Exception as e:
                    self.console.print(f"[red]Error while handling component {custom_id}[/red]")
                    self.client.logger.error(f"Error while handling component {custom_id}: {e}")
                    await self.client.api_helper.send_interaction_response(
                        interaction["id"], interaction["token"], message=f"An error occurred while handling the component.\n`{e}`"
                    )
            else:
                self.console.print(f"[red]No handler found for component with custom_id: {custom_id}[/red]")
                await self.client.api_helper.send_interaction_response(
                    interaction["id"], interaction["token"], message="No handler for this component."
                )

        elif interaction_type == 5:
            custom_id = interaction['data'].get('custom_id', '')
            try:
                await self.handle_modal(interaction, custom_id)
            except Exception as e:
                self.console.print(f"[red]Error while handling modal {custom_id}[/red]")
                self.client.logger.error(f"Error while handling modal {custom_id}: {e}")
                await self.client.api_helper.send_interaction_response(
                    interaction["id"], interaction["token"], message=f"An error occurred while handling the modal. \n`{e}`"
                )

        else:
            self.console.print(f"[red]Unknown interaction type: {interaction_type}[/red]")
            await self.client.api_helper.send_interaction_response(
                interaction["id"], interaction["token"], message="Unknown interaction type"
            )
