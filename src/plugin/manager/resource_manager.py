import logging
from typing import List, Union

from azure.core.exceptions import ResourceNotFoundError, ClientAuthenticationError

from plugin.manager.base import AzureBaseManager
from plugin.connector.subscription_connector import SubscriptionConnector
from plugin.connector.management_groups_connector import ManagementGroupsConnector
from plugin.connector.billing_connector import BillingConnector
from plugin.manager.management_group_manger import ManagementGroupManager

_LOGGER = logging.getLogger("spaceone")


class ResourceManager(AzureBaseManager):
    agreement_type = "Unknown"

    def __init__(self, *args, **kwargs):
        self.management_group_mgr = ManagementGroupManager()
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
        agreement_type = self.agreement_type

        management_group_location_map = {}
        result_subscription_map = {}
        subscription_info_map = {}

        _LOGGER.debug(
            f"[sync] Start sync for tenant_id: {secret_data['tenant_id']}, agreement_type: {self.agreement_type}"
        )

        for tenant in subscription_connector.list_tenants():
            for subscription in subscription_connector.list_subscriptions():
                result = {}
                subscription_info = self.convert_nested_dictionary(subscription)

                tenant_id = tenant.tenant_id
                subscription_status = self.get_subscription_status(
                    subscription_info, agreement_type
                )
                subscription_id = self.get_subscription_id(
                    subscription_info, agreement_type
                )

                if not subscription_id:
                    continue

                inject_secret = False
                if subscription_status in ["Enabled"]:
                    subscription_info_map[subscription_id] = subscription_info
                    subscription_name = self.get_subscription_name(
                        subscription_info, agreement_type
                    )
                    subscription_tags = subscription_info.get("tags", {})

                    location = [
                        {
                            "name": tenant.display_name or "Home",
                            "resource_id": tenant_id,
                        }
                    ]

                    if tenant_id not in management_group_location_map.keys():
                        management_group_location_map = (
                            self.management_group_mgr.get_management_group_location_map(
                                options,
                                secret_data,
                                tenant_id,
                                management_group_location_map,
                            )
                        )

                    if management_group_location_map.get(tenant_id):
                        management_group_location = management_group_location_map[
                            tenant_id
                        ].get(subscription_id)
                        location.extend(management_group_location)

                    if subscription_info_map.get(subscription_id):
                        inject_secret = True

                    result = self.make_result(
                        tenant_id,
                        subscription_id,
                        subscription_name,
                        inject_secret,
                        location,
                        subscription_tags,
                    )

                if result:
                    result_subscription_map[subscription_id] = result

        if result_subscription_map:
            results_info = result_subscription_map.values()
            for result_info in results_info:
                results.append(result_info)

        _LOGGER.debug(f"[sync] total results: {len(results)}")

        return results
