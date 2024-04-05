import logging
import os

from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient, SubscriptionClient
from azure.mgmt.managementgroups import ManagementGroupsAPI
from azure.mgmt.billing import BillingManagementClient
from spaceone.core.connector import BaseConnector

from plugin.error.common import *

__all__ = ["AzureBaseConnector"]

_LOGGER = logging.getLogger("spaceone")


class AzureBaseConnector(BaseConnector):
    connector_name = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def set_connect(self, secret_data: dict, tenant_id: str = None) -> None:
        if tenant_id:
            secret_data["tenant_id"] = tenant_id
        subscription_id = secret_data.get("subscription_id", "")

        os.environ["AZURE_SUBSCRIPTION_ID"] = subscription_id
        os.environ["AZURE_TENANT_ID"] = secret_data["tenant_id"]
        os.environ["AZURE_CLIENT_ID"] = secret_data["client_id"]
        os.environ["AZURE_CLIENT_SECRET"] = secret_data["client_secret"]

        credential = ClientSecretCredential(
            secret_data["tenant_id"],
            secret_data["client_id"],
            secret_data["client_secret"],
            subscription_id=subscription_id,
            additionally_allowed_tenants=["*"],
        )

        self.resource_client: ResourceManagementClient = ResourceManagementClient(
            credential=credential, subscription_id=subscription_id
        )
        self.management_groups_client: ManagementGroupsAPI = ManagementGroupsAPI(
            credential=credential
        )

        self.billing_client: BillingManagementClient = BillingManagementClient(
            credential=credential, subscription_id=subscription_id
        )

        self.subscription_client: SubscriptionClient = SubscriptionClient(
            credential=DefaultAzureCredential()
        )

    def _make_request_headers(self, secret_data, client_type=None):
        access_token = self._get_access_token(secret_data)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        return headers

    @staticmethod
    def _get_access_token(secret_data: dict):
        try:
            credential = ClientSecretCredential(
                additionally_allowed_tenants=["*"], **secret_data
            )
            scopes = ["https://management.azure.com/.default"]
            token_info = credential.get_token(*scopes)
            return token_info.token
        except Exception as e:
            _LOGGER.error(f"[ERROR] _get_access_token :{e}")
            raise ERROR_INVALID_TOKEN(token=e)

    @classmethod
    def get_connector_by_name(cls, name: str, secret_data: dict) -> BaseConnector:
        for sub_cls in cls.__subclasses__():
            if sub_cls.connector_name == name:
                return sub_cls(secret_data)
