import logging
import asyncio

from plugin.connector.base import AzureBaseConnector

_LOGGER = logging.getLogger("spaceone")


class SubscriptionConnector(AzureBaseConnector):
    connector_name = "SubscriptionConnector"

    def __init__(self, *args, **kwargs):
        super().set_connect(*args, **kwargs)
        super().__init__(*args, **kwargs)

    def list_tenants(
        self,
    ) -> list:
        tenants = self.subscription_client.tenants.list()
        return tenants

    def list_subscriptions(self) -> dict:
        subscriptions = self.subscription_client.subscriptions.list()
        return subscriptions
