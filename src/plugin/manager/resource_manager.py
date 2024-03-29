import asyncio
import logging

from plugin.manager.base import AzureBaseManager
from plugin.connector.subscription_connector import SubscriptionConnector
from plugin.connector.management_groups_connector import ManagementGroupsConnector

_LOGGER = logging.getLogger("spaceone")


class ResourceManager(AzureBaseManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def sync(
        self, options: dict, secret_data: dict, domain_id: str, schema_id: str = None
    ) -> list:
        """sync Azure resources
            :Returns:
                results [
                {
                    name: 'str',
                    data: 'dict',
                    secret_schema_id: 'str',
                    secret_data: 'dict',
                    tags: 'dict',
                    location: 'list'
                }
        ]
        """
        results = []

        subscription_connector = SubscriptionConnector(secret_data=secret_data)
        tenants = subscription_connector.list_tenants()

        for tenant in tenants:
            tenant_info = self.convert_nested_dictionary(tenant)
            tenant_id = tenant_info["tenant_id"]

            management_groups_connector = ManagementGroupsConnector()

            entities = management_groups_connector.list_entities(secret_data, tenant_id)

            for entity in entities:
                entity_info = self.convert_nested_dictionary(entity)

                if entity_info.get("type") == "/subscriptions":
                    name = entity_info["display_name"]
                    tenant_id = entity_info["tenant_id"]
                    subscription_id = entity_info["name"]
                    location = entity_info["parent_display_name_chain"]

                    result = {
                        "name": name,
                        "data": {
                            "subscription_id": subscription_id,
                            "tenant_id": tenant_id,
                        },
                        "secret_schema_id": "azure-secret-subscription-id",
                        "secret_data": {
                            "subscription_id": subscription_id,
                        },
                        "tags": entity_info.get("tags", {}) or {},
                        "location": location,
                    }
                    results.append(result)

        return results
