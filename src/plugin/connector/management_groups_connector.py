import logging
import asyncio

from azure.core.exceptions import HttpResponseError
from plugin.connector.base import AzureBaseConnector

_LOGGER = logging.getLogger("spaceone")


class ManagementGroupsConnector(AzureBaseConnector):
    connector_name = "ManagementGroupsConnector"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def list_management_groups(self) -> list:
        management_groups = []
        try:
            management_groups = self.management_groups_client.management_groups.list()
        except HttpResponseError as e:
            _LOGGER.error(f"[list_management_groups] Error: {e}")
        except Exception as e:
            _LOGGER.error(f"[list_management_groups] Error: {e}")

        return management_groups

    def list_entities(self, secret_data: dict, tenant_id: str = None) -> list:
        self.set_connect(secret_data, tenant_id)

        entities = []
        try:
            entities = self.management_groups_client.entities.list()
        except HttpResponseError as e:
            _LOGGER.error(f"[list_entities] Error: {e}")
        except Exception as e:
            _LOGGER.error(f"[list_entities] Error: {e}")
        return entities

    def list_permissions(self, secret_data: dict, tenant_id: str = None) -> list:
        self.set_connect(secret_data, tenant_id)
        operations = self.management_groups_client.operations.list()
        return operations
