import aiohttp

class WebhookManager:
    @classmethod
    def get_headers(cls, client):
        return {
            "Authorization": f"Bot {client.token}",
            "Content-Type": "application/json"
        }

    @classmethod
    async def create_webhook(cls, client, channel_id, name, avatar=None):
        url = f"{client.base_url}/channels/{channel_id}/webhooks"
        headers = cls.get_headers(client)
        data = {
            "name": name,
            "avatar": avatar
        }
        async with client.session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Failed to create webhook: {response.status} - {await response.text()}")

    @classmethod
    async def edit_webhook(cls, client, webhook_id, name=None, avatar=None, channel_id=None):
        url = f"{client.base_url}/webhooks/{webhook_id}"
        headers = cls.get_headers(client)
        data = {}
        if name:
            data["name"] = name
        if avatar:
            data["avatar"] = avatar
        if channel_id:
            data["channel_id"] = channel_id

        async with client.session.patch(url, headers=headers, json=data) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Failed to edit webhook: {response.status} - {await response.text()}")

    @classmethod
    async def get_webhook(cls, client, webhook_id):
        url = f"{client.base_url}/webhooks/{webhook_id}"
        headers = cls.get_headers(client)
        async with client.session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Failed to retrieve webhook: {response.status} - {await response.text()}")

    @classmethod
    async def delete_webhook(cls, client, webhook_id):
        url = f"{client.base_url}/webhooks/{webhook_id}"
        headers = cls.get_headers(client)
        async with client.session.delete(url, headers=headers) as response:
            if response.status == 204:
                print(f"Webhook {webhook_id} deleted successfully.")
            else:
                raise Exception(f"Failed to delete webhook: {response.status} - {await response.text()}")

    @classmethod
    async def send_webhook_message(cls, client, webhook_id, webhook_token, content, embeds=None, username=None, avatar_url=None):
        url = f"{client.base_url}/webhooks/{webhook_id}/{webhook_token}"
        headers = {"Content-Type": "application/json"}
        data = {
            "content": content,
            "embeds": embeds or [],
            "username": username,
            "avatar_url": avatar_url
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status in (200, 204):
                    print("Message sent successfully.")
                else:
                    raise Exception(f"Failed to send message: {response.status} - {await response.text()}")
