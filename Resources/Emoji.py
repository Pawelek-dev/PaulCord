import aiohttp

class EmojiManager:
    @classmethod
    def get_headers(cls, client):
        return {
            "Authorization": f"Bot {client.token}",
            "Content-Type": "application/json"
        }

    @classmethod
    async def get_emojis(cls, client, guild_id):
        url = f"{client.base_url}/guilds/{guild_id}/emojis"
        headers = cls.get_headers(client)

        async with client.session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"Failed to get emojis: {response.status} {await response.text()}")
                return None

    @classmethod
    async def add_emoji(cls, client, guild_id, name, image_base64):
        url = f"{client.base_url}/guilds/{guild_id}/emojis"
        headers = cls.get_headers(client)
        json_data = {
            "name": name,
            "image": image_base64
        }

        async with client.session.post(url, headers=headers, json=json_data) as response:
            if response.status == 201:
                print(f"Successfully added emoji: {name}")
                return await response.json()
            else:
                print(f"Failed to add emoji: {response.status} {await response.text()}")
                return None

    @classmethod
    async def update_emoji(cls, client, guild_id, emoji_id, name=None, image_base64=None):
        url = f"{client.base_url}/guilds/{guild_id}/emojis/{emoji_id}"
        headers = cls.get_headers(client)
        json_data = {}
        if name:
            json_data["name"] = name
        if image_base64:
            json_data["image"] = image_base64

        async with client.session.patch(url, headers=headers, json=json_data) as response:
            if response.status == 200:
                print(f"Successfully updated emoji: {emoji_id}")
                return await response.json()
            else:
                print(f"Failed to update emoji: {response.status} {await response.text()}")
                return None

    @classmethod
    async def delete_emoji(cls, client, guild_id, emoji_id):
        url = f"{client.base_url}/guilds/{guild_id}/emojis/{emoji_id}"
        headers = cls.get_headers(client)

        async with client.session.delete(url, headers=headers) as response:
            if response.status == 204:
                print(f"Successfully deleted emoji: {emoji_id}")
            else:
                print(f"Failed to delete emoji: {response.status} {await response.text()}")
