import aiohttp

class StickerSender:
    @classmethod
    def get_headers(cls, client):
        return {
            "Authorization": f"Bot {client.token}",
            "Content-Type": "application/json"
        }

    @classmethod
    async def send_sticker(cls, client, channel_id, sticker_id):
        url = f"{client.base_url}/channels/{channel_id}/messages"
        headers = cls.get_headers(client)
        payload = {
            "sticker_ids": [sticker_id]
        }

        async with client.session.post(url, headers=headers, json=payload) as response:
            if response.status == 200:
                print("Sticker sent successfully!")
            else:
                print(f"Failed to send sticker: {response.status} - {await response.text()}")
