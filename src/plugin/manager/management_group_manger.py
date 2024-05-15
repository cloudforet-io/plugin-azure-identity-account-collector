import logging
from typing import List

from azure.core.exceptions import ResourceNotFoundError

from plugin.manager.base import AzureBaseManager
from plugin.connector.management_groups_connector import ManagementGroupsConnector

_LOGGER = logging.getLogger("spaceone")


class ManagementGroupManager(AzureBaseManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_management_group_location_map(
        self,
        options: dict,
        secret_data: dict,
        tenant_id: str,
        management_group_location_map: dict,
    ) -> dict:
        try:
            management_groups_connector = ManagementGroupsConnector()
            entities = management_groups_connector.list_entities(secret_data, tenant_id)

            management_group_location_map[tenant_id] = {}

            for entity in entities:
                entity_info = self.convert_nested_dictionary(entity)

                if entity_info.get("type") == "/subscriptions":
                    subscription_id = entity_info["name"]

                    location = self._create_location_from_entity_info(
                        entity_info, options
                    )
                    management_group_location_map[tenant_id][subscription_id] = location

        except ResourceNotFoundError as e:
            _LOGGER.error(
                f"[sync] {e.status_code} {e.message}, Please check the permission. https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/management-and-governance#management-group-reader"
            )

        except Exception as e:
            _LOGGER.error(f"[sync] {e}", exc_info=True)

        return management_group_location_map

    @staticmethod
    def _create_location_from_entity_info(
        entity_info: dict, options: dict
    ) -> List[dict]:
        location = []
        parent_display_name_chain = entity_info.get("parent_display_name_chain", [])
        parent_name_chain = entity_info.get("parent_name_chain", [])
        for idx, name in enumerate(parent_display_name_chain):
            if options.get("exclude_root_management_group") and idx == 0:
                continue
            location.append(
                {
                    "name": name,
                    "resource_id": parent_name_chain[idx],
                }
            )

        return location
