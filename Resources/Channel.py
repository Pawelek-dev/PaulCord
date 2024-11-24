import aiohttp

class ChannelManager:
    @classmethod
    def get_headers(cls, client):
        return {
            "Authorization": f"Bot {client.token}",
            "Content-Type": "application/json"
        }

    @classmethod
    async def create_channel(cls, client, name, type_):
        url = f"{client.base_url}/guilds/{client.get_guild_id()}/channels"
        headers = cls.get_headers(client)
        json_data = {
            "name": name,
            "type": type_
        }

        async with client.session.post(url, headers=headers, json=json_data) as response:
            if response.status == 201:
                return await response.json()
            else:
                print(f"Failed to create channel: {response.status} {await response.text()}")
                return None

    @classmethod
    async def edit_channel(cls, client, channel_id, new_name):
        url = f"{client.base_url}/channels/{channel_id}"
        headers = cls.get_headers(client)
        json_data = {
            "name": new_name
        }

        async with client.session.patch(url, headers=headers, json=json_data) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"Failed to edit channel: {response.status} {await response.text()}")
                return None

    @classmethod
    async def delete_channel(cls, client, channel_id):
        url = f"{client.base_url}/channels/{channel_id}"
        headers = cls.get_headers(client)

        async with client.session.delete(url, headers=headers) as response:
            if response.status == 204:
                return {"status": "Channel deleted successfully"}
            else:
                print(f"Failed to delete channel: {response.status} {await response.text()}")
                return None

    @classmethod
    async def list_channels(cls, client):
        url = f"{client.base_url}/guilds/{client.get_guild_id()}/channels"
        headers = cls.get_headers(client)

        async with client.session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"Failed to list channels: {response.status} {await response.text()}")
                return None
