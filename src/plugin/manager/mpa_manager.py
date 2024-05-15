import logging
from typing import List, Union

from azure.core.exceptions import ClientAuthenticationError

from plugin.manager.base import AzureBaseManager
from plugin.connector.subscription_connector import SubscriptionConnector
from plugin.connector.billing_connector import BillingConnector
from plugin.manager.management_group_manger import ManagementGroupManager

_LOGGER = logging.getLogger("spaceone")


class MPAManager(AzureBaseManager):
    agreement_type = "MicrosoftPartnerAgreement"

    def __init__(self, *args, **kwargs):
        self.management_group_mgr = ManagementGroupManager()
        super().__init__(*args, **kwargs)

    def sync(
        self,
        options: dict,
        secret_data: dict,
        domain_id: str,
        billing_account_id: str,
        schema_id: str = None,
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

        billing_connector = BillingConnector(secret_data=secret_data)
        agreement_type = self.agreement_type

        management_group_location_map = {}
        result_subscription_map = {}
        subscription_info_map = {}

        _LOGGER.debug(
            f"[sync] Start sync for tenant_id: {secret_data['tenant_id']}, agreement_type: {self.agreement_type}"
        )

        for subscription in billing_connector.list_subscription(
            options, secret_data, agreement_type, billing_account_id
        ):
            result = {}

            subscription_info = self.convert_nested_dictionary(subscription)
            subscription_status = self._get_subscription_status(
                subscription_info, agreement_type
            )
            subscription_id = self._get_subscription_id(
                subscription_info, agreement_type
            )

            if not subscription_id:
                continue

            inject_secret = False
            if subscription_status in ["Active"]:
                tenant_id = self._get_tenant_id_from_customer_id(
                    subscription_info.get("customer_id")
                )
                subscription_name = self.get_subscription_name(
                    subscription_info, agreement_type
                )

                location = self._get_customer_location(subscription_info, tenant_id)

                # Check Management Group Location
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

                if subscription_info_map.get("subscription_id") is None:
                    subscription_info_map = self._get_subscription_info_map(
                        subscription_info_map, secret_data, tenant_id
                    )

                if subscription_info_map.get(subscription_id):
                    inject_secret = True

                result = self.make_result(
                    tenant_id,
                    subscription_id,
                    subscription_name,
                    inject_secret,
                    location,
                )

            if result:
                result_subscription_map[subscription_id] = result

        if result_subscription_map:
            results_info = result_subscription_map.values()
            for result_info in results_info:
                results.append(result_info)

        _LOGGER.debug(f"[sync] total results: {len(results)}")

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
    def _get_tenant_id_from_customer_id(customer_id: str) -> str:
        return customer_id.split("/")[-1]

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
    def _get_customer_location(subscription_info: dict, resource_id: str) -> List[dict]:
        location = []
        location_name = subscription_info["customer_display_name"]
        location_name = location_name.strip()

        location.append(
            {
                "name": location_name,
                "resource_id": resource_id,
            }
        )
        return location
