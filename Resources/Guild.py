import aiohttp
import asyncio

class Guild:
    def __init__(self, client, guild_id):
        self.client = client
        self.guild_id = guild_id

    async def fetch_member(self, user_id):
        url = f"{self.client.base_url}/members/{user_id}"
        headers = {
            "Authorization": f"Bot {self.client.token}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    member_data = await response.json()
                    return member_data
                else:
                    print(f"Failed to fetch member {user_id}: {response.status} - {await response.text()}")
                    return None

    async def fetch_guild(self):
        url = self.client.base_url
        headers = {
            "Authorization": f"Bot {self.client.token}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    guild_data = await response.json()
                    return guild_data
                else:
                    print(f"Failed to fetch guild {self.guild_id}: {response.status} - {await response.text()}")
                    return None

    def get_display_name(self, member_data):
        return member_data.get('nick') or member_data['user']['username']

    def get_username(self, member_data):
        return member_data['user']['username']

    def get_profile_avatar(self, member_data):
        avatar = member_data['user'].get('avatar')
        if avatar:
            return f"https://cdn.discordapp.com/avatars/{member_data['user']['id']}/{avatar}.png"
        return None
