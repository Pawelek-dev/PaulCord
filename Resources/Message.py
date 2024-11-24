import aiohttp
import sys

class Message:
    def __init__(self, client, id, channel_id, author, content, timestamp, edited_timestamp=None, tts=False, 
                 mention_everyone=False, mentions=None, mention_roles=None, mention_channels=None, 
                 attachments=None, embeds=None, reactions=None, nonce=None, pinned=False, 
                 webhook_id=None, type=0, activity=None, application=None, application_id=None, 
                 flags=None, message_reference=None, message_snapshots=None, referenced_message=None, 
                 interaction_metadata=None, interaction=None, thread=None, components=None, 
                 sticker_items=None, stickers=None, position=None, role_subscription_data=None, 
                 resolved=None, call=None):
        self.client = client
        self.id = id
        self.channel_id = channel_id
        self.author = author
        self.content = content
        self.timestamp = timestamp
        self.edited_timestamp = edited_timestamp
        self.tts = tts
        self.mention_everyone = mention_everyone
        self.mentions = mentions if mentions is not None else []
        self.mention_roles = mention_roles if mention_roles is not None else []
        self.mention_channels = mention_channels if mention_channels is not None else []
        self.attachments = attachments if attachments is not None else []
        self.embeds = embeds if embeds is not None else []
        self.reactions = reactions if reactions is not None else []
        self.nonce = nonce
        self.pinned = pinned
        self.webhook_id = webhook_id
        self.type = type
        self.activity = activity
        self.application = application
        self.application_id = application_id
        self.flags = flags
        self.message_reference = message_reference
        self.message_snapshots = message_snapshots if message_snapshots is not None else []
        self.referenced_message = referenced_message
        self.interaction_metadata = interaction_metadata
        self.interaction = interaction
        self.thread = thread
        self.components = components if components is not None else []
        self.sticker_items = sticker_items if sticker_items is not None else []
        self.stickers = stickers if stickers is not None else []
        self.position = position
        self.role_subscription_data = role_subscription_data
        self.resolved = resolved
        self.call = call

    @classmethod
    def get_headers(cls, client):
        return {
            "Authorization": f"Bot {client.token}",
            "Content-Type": "application/json"
        }

    @classmethod
    async def get_message(cls, client, channel_id, message_id):
        url = f"{client.base_url}/channels/{channel_id}/messages/{message_id}"
        headers = cls.get_headers(client)
        async with client.session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Błąd podczas pobierania wiadomości: {response.status} {await response.text()}")

    @classmethod
    async def create_message(cls, client, channel_id, content, tts=False, embeds=None, allowed_mentions=None):
        url = f"{client.base_url}/channels/{channel_id}/messages"
        headers = cls.get_headers(client)
        data = {
            "content": content,
            "tts": tts,
            "embeds": embeds or [],
            "allowed_mentions": allowed_mentions or {}
        }
        async with client.session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Error creating message: {response.status} {await response.text()}")

    @classmethod
    async def edit_message(cls, client, channel_id, message_id, content=None, embeds=None, allowed_mentions=None):
        url = f"{client.base_url}/channels/{channel_id}/messages/{message_id}"
        headers = cls.get_headers(client)
        data = {
            "content": content,
            "embeds": embeds or [],
            "allowed_mentions": allowed_mentions or {}
        }
        async with client.session.patch(url, headers=headers, json=data) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Error editing message: {response.status} {await response.text()}")

    @classmethod
    async def delete_message(cls, client, channel_id, message_id):
        url = f"{client.base_url}/channels/{channel_id}/messages/{message_id}"
        headers = cls.get_headers(client)
        async with client.session.delete(url, headers=headers) as response:
            if response.status == 204:
                print(f"Message {message_id} deleted.")
            else:
                raise Exception(f"Error deleting message: {response.status} {await response.text()}")

    @classmethod
    async def get_message(cls, client, channel_id, message_id):
        url = f"{client.base_url}/channels/{channel_id}/messages/{message_id}"
        headers = cls.get_headers(client)
        async with client.session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Error fetching message: {response.status} {await response.text()}")

    @classmethod
    async def add_reaction(cls, client, channel_id, message_id, emoji):
        url = f"{client.base_url}/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me"
        headers = cls.get_headers(client)
        async with client.session.put(url, headers=headers) as response:
            if response.status == 204:
                print(f"Reaction {emoji} added to message {message_id}.")
            else:
                raise Exception(f"Error adding reaction: {response.status} {await response.text()}")

    @classmethod
    async def remove_reaction(cls, client, channel_id, message_id, emoji):
        url = f"{client.base_url}/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me"
        headers = cls.get_headers(client)
        async with client.session.delete(url, headers=headers) as response:
            if response.status == 204:
                print(f"Reaction {emoji} removed from message {message_id}.")
            else:
                raise Exception(f"Error removing reaction: {response.status} {await response.text()}")

    @classmethod
    async def remove_all_reactions(cls, client, channel_id, message_id):
        url = f"{client.base_url}/channels/{channel_id}/messages/{message_id}/reactions"
        headers = cls.get_headers(client)
        async with client.session.delete(url, headers=headers) as response:
            if response.status == 204:
                print(f"All reactions removed from message {message_id}.")
            else:
                raise Exception(f"Error removing all reactions: {response.status} {await response.text()}")

    @classmethod
    async def pin_message(cls, client, channel_id, message_id):
        url = f"{client.base_url}/channels/{channel_id}/pins/{message_id}"
        headers = cls.get_headers(client)
        async with client.session.put(url, headers=headers) as response:
            if response.status == 204:
                print(f"Message {message_id} pinned.")
            else:
                raise Exception(f"Error pinning message: {response.status} {await response.text()}")

    @classmethod
    async def unpin_message(cls, client, channel_id, message_id):
        url = f"{client.base_url}/channels/{channel_id}/pins/{message_id}"
        headers = cls.get_headers(client)
        async with client.session.delete(url, headers=headers) as response:
            if response.status == 204:
                print(f"Message {message_id} unpinned.")
            else:
                raise Exception(f"Error unpinning message: {response.status} {await response.text()}")

    @classmethod
    async def crosspost_message(cls, client, channel_id, message_id):
        url = f"{client.base_url}/channels/{channel_id}/messages/{message_id}/crosspost"
        headers = cls.get_headers(client)
        async with client.session.post(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Error crossposting message: {response.status} {await response.text()}")
            
            
    
