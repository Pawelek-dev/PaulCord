import asyncio
import aiohttp
import json
import time

from PaulCord.Core.CommandRegistration import CommandRegistration
from PaulCord.Core.WebSocketConnection import WebSocketConnection
from PaulCord.Core.Decorators import CommandDecorator, ComponentHandlerDecorator
from PaulCord.Core.Intents import Intents

class Client:
    def __init__(self, token, application_id, shard_id=0, total_shards=1, intents=Intents.default):
        self.token = token
        self.application_id = application_id
        self.shard_id = shard_id
        self.base_url = "https://discord.com/api/v10"
        self.gateway_url = "wss://gateway.discord.gg/?v=10&encoding=json"
        self.session = None
        self.ws = None
        self.sequence = None
        self.heartbeat_interval = None
        self.running = True
        self.commands = []
        self.component_handlers = {}
        self.last_heartbeat_ack = True
        self.session_id = None
        self.reconnect_attempts = 0
        self.intents = intents
        self.total_shards = total_shards
        self.events = {}

        self.command_registration = CommandRegistration(self)
        self.websocket_connection = WebSocketConnection(self)
        self.command_decorator = CommandDecorator(self)
        self.component_handler_decorator = ComponentHandlerDecorator(self)

    def event(self, func):  
        self.events[func.__name__] = func
        return func

    def slash_commands(self, name=None, description=None):
        return self.command_decorator.slash_commands(name, description)

    def handle_component(self, interaction, custom_id):
        handler = self.component_handler_decorator.component_handlers.get(custom_id)
        if handler:
            handler(self, interaction)
        else:
            print(f"No handler found for component with custom_id: {custom_id}")
            self.send_interaction_response(interaction["id"], interaction["token"], message="No handler for this component.")

    async def fetch_guild_count(self):
        url = f"{self.base_url}/users/@me/guilds"
        headers = {
            "Authorization": f"Bot {self.token}"
        }
        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    guilds = await response.json()
                    return len(guilds)
                else:
                    text = await response.text()
                    print(f"Failed to fetch guild count: {response.status} {text}")
                    return None
        except Exception as e:
            print(f"Error fetching guild count: {e}")
            return None

    async def handle_interaction(self, interaction):
        print(f"Handling interaction: {interaction}")
        interaction_type = interaction['type']

        if interaction_type == 2:
            command_name = interaction['data']['name']
            print(f"Received slash command: {command_name}")
            command = next((cmd for cmd in self.commands if cmd['name'] == command_name), None)

            if command:
                try:
                    print(f"Executing command: {command_name}")
                    result_message = await command['func'](self, interaction)

                    if result_message:
                        print(f"Sending interaction response for command: {command_name}")
                        await self.send_interaction_response(
                            interaction["id"],
                            interaction["token"],
                            message=result_message
                        )
                    else:
                        print(f"No response message for command {command_name}, skipping send.")
                except Exception as e:
                    print(f"Error while executing command {command_name}: {e}")
                    await self.send_interaction_response(
                        interaction["id"],
                        interaction["token"],
                        message="An error occurred while executing the command."
                    )
            else:
                print(f"Unknown command: {command_name}")
                await self.send_interaction_response(interaction["id"], interaction["token"], message="Unknown command")

        elif interaction_type == 3:
            custom_id = interaction['data'].get('custom_id', '')
            print(f"Handling component with custom_id: {custom_id}")
            handler = self.component_handler_decorator.component_handlers.get(custom_id)
            if handler:
                try:
                    await handler(self, interaction)
                except Exception as e:
                    print(f"Error while handling component {custom_id}: {e}")
                    await self.send_interaction_response(interaction["id"], interaction["token"], message="An error occurred while handling the component.")
            else:
                print(f"No handler found for component with custom_id: {custom_id}")
                await self.send_interaction_response(interaction["id"], interaction["token"], message="No handler for this component.")

        elif interaction_type == 5:
            custom_id = interaction['data'].get('custom_id', '')
            try:
                await self.handle_modal(interaction, custom_id)
            except Exception as e:
                print(f"Error while handling modal {custom_id}: {e}")
                await self.send_interaction_response(interaction["id"], interaction["token"], message="An error occurred while handling the modal.")

        else:
            print(f"Unknown interaction type: {interaction_type}")
            await self.send_interaction_response(interaction["id"], interaction["token"], message="Unknown interaction type")



    async def dispatch_event(self, event_name, *args, **kwargs):
        if event_name in self.events:
            await self.events[event_name](*args, **kwargs)
        else:
            print(f"No handler for event: {event_name}")

    async def send_acknowledgement(self, interaction_id, interaction_token):
        url = f"{self.base_url}/interactions/{interaction_id}/{interaction_token}/callback"
        json_data = {
            "type": 5
        }
        async with self.session.post(url, json=json_data) as response:
            if response.status != 200:
                text = await response.text()
                print(f"Failed to send interaction acknowledgement: {response.status} {text}")
            else:
                print("Interaction acknowledgement sent successfully")

    async def send_final_response(self, interaction_token, message=None, embed=None, ephemeral=False, components=None):
        url = f"{self.base_url}/webhooks/{self.application_id}/{interaction_token}"
        json_data = {}

        if message:
            json_data["content"] = message

        if embed:
            json_data["embeds"] = [embed]

        if components:
            json_data["components"] = components

        if ephemeral:
            json_data["flags"] = 64
        async with self.session.post(url, json=json_data) as response:
            if response.status != 200:
                text = await response.text()
                print(f"Failed to send final response: {response.status} {text}")
            else:
                print("Final interaction response sent successfully")

    async def send_interaction_response(self, interaction_id, interaction_token, message=None, embed=None, ephemeral=False, components=None):
        url = f"{self.base_url}/interactions/{interaction_id}/{interaction_token}/callback"

        if not message and not embed and not components:
            message = "Default response content" 

        json_data = {
            "type": 4, 
            "data": {}
        }

        if message:
            json_data["data"]["content"] = message

        if ephemeral:
            json_data["data"]["flags"] = 64

        if embed:
            json_data["data"]["embeds"] = [embed]

        if components:
            json_data["data"]["components"] = components

        try:
            async with self.session.post(url, json=json_data) as response:
                if response.status != 200:
                    text = await response.text()
                    print(f"Failed to send interaction response: {response.status} {text}")
                else:
                    print("Interaction response sent successfully")
        except Exception as e:
            print(f"An error occurred while sending interaction response: {e}")


    async def edit_interaction_response(self, interaction_token, message=None, ephemeral=False, embed=None, components=None):
        url = f"{self.base_url}/webhooks/{self.application_id}/{interaction_token}/messages/@original"
        json_data = {}

        if message:
            json_data["content"] = message

        if embed:
            json_data["embeds"] = [embed]

        if components:
            json_data["components"] = components

        if ephemeral:
            json_data["flags"] = 64

        try:
            async with self.session.patch(url, json=json_data) as response:
                if response.status != 200:
                    text = await response.text()
                    print(f"Failed to edit interaction response: {response.status} {text}")
                else:
                    print("Interaction response edited successfully")
        except Exception as e:
            print(f"An error occurred while editing interaction response: {e}")

    def count_registered_commands(self):
        return len(self.commands)



    async def main(self):
        print("Starting command registration and sync.")
        print(f"Commands before registration: {self.commands}")

        try:
            await self.command_registration.register_commands()
            print("Commands registered.")
        except Exception as e:
            print(f"Error during command registration: {e}")

        try:
            await self.command_registration.sync_commands()
            print("Commands synchronized.")
        except Exception as e:
            print(f"Error during command synchronization: {e}")

        try:
            await self.websocket_connection.connect()
            print("WebSocket connection established.")
        except Exception as e:
            print(f"Error during WebSocket connection: {e}")

    async def run_async(self):
        self.session = aiohttp.ClientSession()
        await self.main()
        await self.session.close()

    def run(self):
        asyncio.run(self.run_async())
