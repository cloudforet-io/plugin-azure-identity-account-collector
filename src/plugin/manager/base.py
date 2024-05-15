import logging
from typing import Union, List

from spaceone.core.manager import BaseManager

from plugin.connector.billing_connector import BillingConnector

_LOGGER = logging.getLogger("spaceone")


class AzureBaseManager(BaseManager):
    provider = "azure"
    agreement_type = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def sync(self, *args, **kwargs) -> list:
        """
        Args:
            options: dict,
            secret_data: dict,
            domain_id: str,
            billing_account_id:str = None,
            schema_id: str = None,


        """
        raise NotImplementedError("Method not implemented!")

    def convert_nested_dictionary(self, cloud_svc_object):
        cloud_svc_dict = {}
        if hasattr(
            cloud_svc_object, "__dict__"
        ):  # if cloud_svc_object is not a dictionary type but has dict method
            cloud_svc_dict = cloud_svc_object.__dict__
        elif isinstance(cloud_svc_object, dict):
            cloud_svc_dict = cloud_svc_object
        elif not isinstance(
            cloud_svc_object, list
        ):  # if cloud_svc_object is one of type like int, float, char, ...
            return cloud_svc_object

        # if cloud_svc_object is dictionary type
        for key, value in cloud_svc_dict.items():
            if hasattr(value, "__dict__") or isinstance(value, dict):
                cloud_svc_dict[key] = self.convert_nested_dictionary(value)
            if "azure" in str(type(value)):
                cloud_svc_dict[key] = self.convert_nested_dictionary(value)
            elif isinstance(value, list):
                value_list = []
                for v in value:
                    value_list.append(self.convert_nested_dictionary(v))
                cloud_svc_dict[key] = value_list

        return cloud_svc_dict

    @staticmethod
    def list_billing_accounts(secret_data: dict) -> list:
        billing_connector = BillingConnector(secret_data=secret_data)
        return billing_connector.list_billing_accounts(secret_data=secret_data)

    @staticmethod
    def get_subscription_status(subscription_info: dict, agreement_type: str) -> str:
        if agreement_type == "EnterpriseAgreement":
            return (
                subscription_info.get("properties", {})
                .get("enrollmentAccountSubscriptionDetails", {})
                .get("subscriptionEnrollmentAccountStatus", "")
            )
        elif agreement_type == "MicrosoftPartnerAgreement":
            return subscription_info.get("subscription_billing_status", "")
        else:
            return subscription_info.get("state", "")

    @staticmethod
    def get_subscription_id(
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
    def get_subscription_name(subscription_info: dict, agreement_type: str) -> str:
        if agreement_type == "EnterpriseAgreement":
            return subscription_info.get("properties", {}).get("displayName", "")
        else:
            return subscription_info["display_name"]

    @staticmethod
    def make_result(
        tenant_id: str,
        subscription_id: str,
        name: str,
        inject_secret: bool,
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
        if inject_secret:
            result.update(
                {
                    "secret_schema_id": "azure-secret-multi-tenant",
                    "secret_data": {
                        "subscription_id": subscription_id,
                        "tenant_id": tenant_id,
                    },
                }
            )
        return result

    @classmethod
    def get_all_managers(cls, options) -> list:
        return cls.__subclasses__()

    @classmethod
    def get_manager_by_agreement_type(cls, agreement_type: str):
        for subclass in cls.__subclasses__():
            if subclass.agreement_type == agreement_type:
                return subclass
