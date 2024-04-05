import logging
import asyncio

from azure.core.exceptions import ClientAuthenticationError

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

    def get_subscription(
        self, secret_data: dict, subscription_id: str, tenant_id: str = None
    ) -> dict:
        try:
            if tenant_id:
                self.set_connect(secret_data, tenant_id)
            subscription = self.subscription_client.subscriptions.get(subscription_id)
            return subscription
        except ClientAuthenticationError as e:
            _LOGGER.error(f"[get_subscription] {e.message} => SKIP")
            return {}
