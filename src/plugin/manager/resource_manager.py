import logging
from typing import List, Union

from azure.core.exceptions import ResourceNotFoundError, ClientAuthenticationError

from plugin.manager.base import AzureBaseManager
from plugin.connector.subscription_connector import SubscriptionConnector
from plugin.connector.management_groups_connector import ManagementGroupsConnector
from plugin.connector.billing_connector import BillingConnector

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
        billing_connector = BillingConnector(secret_data=secret_data)

        billing_accounts = billing_connector.list_billing_accounts(
            secret_data=secret_data
        )

        for billing_account in billing_accounts:
            billing_account_info = self.convert_nested_dictionary(billing_account)
            billing_account_id = billing_account_info["name"]
            agreement_type = billing_account_info.get("agreement_type", "")

            result_subscription_map = {}
            subscription_info_map = {}
            for subscription in billing_connector.list_subscription(
                secret_data, agreement_type, billing_account_id
            ):
                subscription_info = self.convert_nested_dictionary(subscription)
                subscription_status = self._get_subscription_status(
                    subscription_info, agreement_type
                )
                subscription_id = self._get_subscription_id(
                    subscription_info, agreement_type
                )

                if subscription_status in ["Active"] and subscription_id:
                    tenant_id = self._get_tenant_id(
                        secret_data, subscription_info, agreement_type
                    )

                    name = self._get_subscription_name(
                        subscription_info, agreement_type
                    )

                    location = self._get_location(
                        subscription_info, agreement_type, tenant_id
                    )

                    if subscription_info_map.get("subscription_id") is None:
                        subscription_info_map = self._get_subscription_info_map(
                            subscription_info_map, secret_data, tenant_id
                        )

                    if subscription_info_map.get(subscription_id):
                        result = self._make_result(
                            tenant_id, subscription_id, name, location
                        )
                    else:
                        result = self._make_result_without_secret(
                            tenant_id, subscription_id, name, location
                        )
                    result_subscription_map[subscription_id] = result
            if agreement_type == "EnterpriseAgreement":
                departments = billing_connector.list_departments(
                    secret_data, billing_account_id
                )

            tenants = subscription_connector.list_tenants()
            try:
                for tenant in tenants:
                    tenant_info = self.convert_nested_dictionary(tenant)
                    tenant_id = tenant_info["tenant_id"]

                    management_groups_connector = ManagementGroupsConnector()
                    entities = management_groups_connector.list_entities(
                        secret_data, tenant_id
                    )

                    for entity in entities:
                        entity_info = self.convert_nested_dictionary(entity)

                        if entity_info.get("type") == "/subscriptions":
                            name = entity_info["display_name"]
                            tenant_id = entity_info["tenant_id"]
                            subscription_id = entity_info["name"]
                            tags = entity_info.get("tags", {})
                            if result := result_subscription_map.get(subscription_id):
                                location = result["location"]
                                location.extend(
                                    self._create_location_from_entity_info(
                                        entity_info, options
                                    )
                                )
                                result.update(
                                    {
                                        "tags": tags,
                                        "location": location,
                                        "secret_schema_id": "azure-secret-multi-tenant",
                                        "secret_data": {
                                            "subscription_id": subscription_id,
                                            "tenant_id": tenant_id,
                                        },
                                    }
                                )
                                if result["data"].get("tenant_id") is None:
                                    result["data"]["tenant_id"] = tenant_id

                                # remove tenant from result_tenant_map
                                result_subscription_map.pop(subscription_id)
                            else:
                                location = self._create_location_from_entity_info(
                                    entity_info, options
                                )
                                result = self._make_result(
                                    tenant_id, subscription_id, name, location, tags
                                )
                            results.append(result)
            except ResourceNotFoundError as e:
                _LOGGER.error(
                    f"[sync] {e.status_code} {e.message}, Please check the permission. https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles/management-and-governance#management-group-reader"
                )
            except Exception as e:
                _LOGGER.error(f"[sync] {e}", exc_info=True)

            if result_subscription_map:
                results_info = result_subscription_map.values()
                for result_info in results_info:
                    if result_info.get("data").get("tenant_id"):
                        results.append(result_info)

        return results

    def _get_subscription_info_map(
        self, subscription_info_map: dict, secret_data: dict, tenant_id: str
    ) -> dict:
        try:
            subscription_connector = SubscriptionConnector(
                secret_data=secret_data, tenant_id=tenant_id
            )
            subscriptions = subscription_connector.list_subscriptions()
            for subscription in subscriptions:
                subscription_info = self.convert_nested_dictionary(subscription)
                subscription_id = subscription_info.get("subscription_id")
                if subscription_id:
                    subscription_info_map[subscription_id] = subscription_info
        except ClientAuthenticationError as e:
            pass
        except Exception as e:
            _LOGGER.error(f"[_get_subscription_info_map] {e}", exc_info=True)

        return subscription_info_map

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

    @staticmethod
    def _get_subscription_status(subscription_info: dict, agreement_type: str) -> str:
        if agreement_type == "EnterpriseAgreement":
            return (
                subscription_info.get("properties", {})
                .get("enrollmentAccountSubscriptionDetails", {})
                .get("subscriptionEnrollmentAccountStatus", "")
            )
        else:
            return subscription_info.get("subscription_billing_status", "")

    @staticmethod
    def _get_tenant_id(
        secret_data: dict, subscription_info: dict, agreement_type: str
    ) -> Union[str, None]:
        if agreement_type == "MicrosoftPartnerAgreement":
            tenant_id = subscription_info.get("customer_id").split("/")[-1]
        else:
            tenant_id = secret_data["tenant_id"]
        return tenant_id

    @staticmethod
    def _get_subscription_id(
        subscription_info: dict, agreement_type: str
    ) -> Union[str, None]:
        if agreement_type == "EnterpriseAgreement":
            subscription_id = subscription_info["properties"]["subscriptionId"]
        else:
            subscription_id = subscription_info["subscription_id"]

        if subscription_id:
            subscription_id = subscription_id.lower()

        return subscription_id

    @staticmethod
    def _get_subscription_name(subscription_info: dict, agreement_type: str) -> str:
        if agreement_type == "EnterpriseAgreement":
            return subscription_info.get("properties", {}).get("displayName", "")
        else:
            return subscription_info["display_name"]

    @staticmethod
    def _get_location(
        subscription_info: dict, agreement_type: str, resource_id: str = None
    ) -> List[dict]:
        location = []

        if agreement_type == "EnterpriseAgreement":
            properties_info = subscription_info.get("properties", {})
            location_name = properties_info["enrollmentAccountDisplayName"]
            resource_id = properties_info["enrollmentAccountId"]
        else:
            location_name = subscription_info.get("customer_display_name", "")

        if location_name and resource_id:
            location = [
                {
                    "name": location_name,
                    "resource_id": resource_id,
                }
            ]
        return location

    @staticmethod
    def _make_result(
        tenant_id: str,
        subscription_id: str,
        name: str,
        location: Union[List[dict], None],
        tags: dict = None,
    ) -> dict:
        result = {
            "name": name,
            "data": {
                "subscription_id": subscription_id,
                "tenant_id": tenant_id,
            },
            "secret_schema_id": "azure-secret-multi-tenant",
            "secret_data": {
                "subscription_id": subscription_id,
                "tenant_id": tenant_id,
            },
            "resource_id": subscription_id,
            "tags": tags,
            "location": location,
        }
        return result

    @staticmethod
    def _make_result_without_secret(
        tenant_id: str,
        subscription_id: str,
        name: str,
        location: Union[List[dict], None],
        tags: dict = None,
    ) -> dict:
        result = {
            "name": name,
            "data": {
                "subscription_id": subscription_id,
                "tenant_id": tenant_id,
            },
            "resource_id": subscription_id,
            "tags": tags,
            "location": location,
        }
        return result
