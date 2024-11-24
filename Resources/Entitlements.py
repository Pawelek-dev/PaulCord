import aiohttp

class EntitlementManager:
    @classmethod
    def get_headers(cls, client):
        return {
            "Authorization": f"Bot {client.token}",
            "Content-Type": "application/json"
        }

    @classmethod
    async def list_entitlements(cls, client, application_id, sku_ids=None, user_id=None, guild_id=None):
        params = {"application_id": application_id}
        if sku_ids:
            params["sku_ids"] = ",".join(sku_ids)
        if user_id:
            params["user_id"] = user_id
        if guild_id:
            params["guild_id"] = guild_id

        url = f"{client.base_url}/entitlements"
        headers = cls.get_headers(client)

        async with client.session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"Failed to list entitlements: {response.status} - {await response.text()}")
                return None

    @classmethod
    async def consume_entitlement(cls, client, entitlement_id):
        url = f"{client.base_url}/entitlements/{entitlement_id}/consume"
        headers = cls.get_headers(client)

        async with client.session.post(url, headers=headers) as response:
            if response.status == 204:
                print(f"Entitlement {entitlement_id} consumed successfully.")
                return True
            else:
                print(f"Failed to consume entitlement: {response.status} - {await response.text()}")
                return False

    @classmethod
    async def create_test_entitlement(cls, client, application_id, sku_id, user_id, guild_id=None):
        url = f"{client.base_url}/entitlements/test-entitlements"
        headers = cls.get_headers(client)
        data = {
            "application_id": application_id,
            "sku_id": sku_id,
            "user_id": user_id,
            "guild_id": guild_id
        }

        async with client.session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"Failed to create test entitlement: {response.status} - {await response.text()}")
                return None

    @classmethod
    async def delete_test_entitlement(cls, client, entitlement_id):
        url = f"{client.base_url}/entitlements/test-entitlements/{entitlement_id}"
        headers = cls.get_headers(client)

        async with client.session.delete(url, headers=headers) as response:
            if response.status == 204:
                print(f"Test entitlement {entitlement_id} deleted successfully.")
                return True
            else:
                print(f"Failed to delete test entitlement: {response.status} - {await response.text()}")
                return False
