import logging
from typing import List

from plugin.connector.billing_connector import BillingConnector
from plugin.connector.subscription_connector import SubscriptionConnector
from plugin.manager.base import AzureBaseManager
from plugin.manager.management_group_manger import ManagementGroupManager

_LOGGER = logging.getLogger("spaceone")


class EAManager(AzureBaseManager):
    agreement_type = "EnterpriseAgreement"

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
    ) -> List[dict]:
        results = []

        billing_connector = BillingConnector(secret_data)
        subscription_connector = SubscriptionConnector(secret_data)

        management_group_location_map = {}
        tenant_id = secret_data["tenant_id"]

        _LOGGER.debug(
            f"[sync] Start sync for tenant_id: {tenant_id}, agreement_type: {self.agreement_type}"
        )

        for department in billing_connector.list_departments(
            secret_data, billing_account_id
        ):
            department_id = department["name"]
            department_name = department.get("properties", {}).get("departmentName")

            for subscription in billing_connector.list_subscription_by_department(
                options, secret_data, department_id, billing_account_id
            ):
                subscription_info = self.convert_nested_dictionary(subscription)
                subscription_status = self.get_subscription_status(
                    subscription_info, self.agreement_type
                )

                subscription_id = self.get_subscription_id(
                    subscription_info, self.agreement_type
                )

                if not subscription_id:
                    continue

                inject_secret = False
                if subscription_status in ["Active"]:
                    subscription_name = self.get_subscription_name(
                        subscription_info, self.agreement_type
                    )

                    location = [{"name": department_name, "resource_id": department_id}]

                    if not options.get("exclude_enrollment_account", False):
                        location = self._get_enrollment_account_location(
                            subscription_info, location
                        )

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

                    subscription_info = self.convert_nested_dictionary(
                        subscription_connector.get_subscription(
                            secret_data, subscription_id
                        )
                    )

                    if subscription_info:
                        inject_secret = True
                        subscription_tags = subscription_info.get("tags", {})
                    else:
                        subscription_tags = {}

                    result = self.make_result(
                        tenant_id,
                        subscription_id,
                        subscription_name,
                        inject_secret,
                        location,
                        subscription_tags,
                    )

                    results.append(result)

        return results

    @staticmethod
    def _get_enrollment_account_location(
        subscription_info: dict, location: list
    ) -> List[dict]:
        properties_info = subscription_info.get("properties", {})
        location_name = properties_info["enrollmentAccountDisplayName"]
        resource_id = properties_info["enrollmentAccountId"]

        location.append({"name": location_name, "resource_id": resource_id})
        return location
