import logging
import os

from msgraph import GraphServiceClient
from azure.identity import (
    DefaultAzureCredential,
    OnBehalfOfCredential,
    ClientSecretCredential,
    UsernamePasswordCredential,
)

# from azure.identity.aio import ClientSecretCredential
from azure.mgmt.resource import ResourceManagementClient, SubscriptionClient
from azure.mgmt.managementgroups import ManagementGroupsAPI
from spaceone.core.error import *
from spaceone.core.connector import BaseConnector

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

        # credential = DefaultAzureCredential(additionally_allowed_tenants=["*"])
        # print(credential)

        credential = ClientSecretCredential(
            secret_data["tenant_id"],
            secret_data["client_id"],
            secret_data["client_secret"],
            additionally_allowed_tenants=["*"],
        )
        # print(credential)
        #
        # credential = UsernamePasswordCredential(
        #     username="rlaalsgh5151@naver.com",
        #     password="Alsehf2187!",
        #     client_id="bdd1bdbf-ce00-4a0d-ad6f-b6ce53247b94",
        # )
        # scopes = ["https://graph.microsoft.com/.default"]
        # self.graph_client = GraphServiceClient(credential, scopes)

        self.resource_client: ResourceManagementClient = ResourceManagementClient(
            credential=credential, subscription_id=subscription_id
        )
        self.subscription_client: SubscriptionClient = SubscriptionClient(
            credential=credential
        )
        self.management_groups_client: ManagementGroupsAPI = ManagementGroupsAPI(
            credential=credential
        )

    @classmethod
    def get_connector_by_name(cls, name: str, secret_data: dict) -> BaseConnector:
        for sub_cls in cls.__subclasses__():
            if sub_cls.connector_name == name:
                return sub_cls(secret_data)
