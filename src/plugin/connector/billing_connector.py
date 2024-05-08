import logging
import requests

from spaceone.core.error import ERROR_UNKNOWN

from plugin.connector.base import AzureBaseConnector

_LOGGER = logging.getLogger("spaceone")


class BillingConnector(AzureBaseConnector):
    connector_name = "BillingConnector"

    def __init__(self, *args, **kwargs):
        super().set_connect(*args, **kwargs)
        super().__init__(*args, **kwargs)
        self.next_link = None

    def list_billing_accounts(self, secret_data: dict) -> list:
        billing_accounts = self.billing_client.billing_accounts.list(
            api_version="2022-10-01-privatepreview"
        )
        return list(billing_accounts)

    def list_customers(self, billing_account_id: str) -> list:
        customers = self.billing_client.customers.list_by_billing_account(
            billing_account_name=billing_account_id
        )
        return list(customers)

    def list_departments(self, secret_data: dict, billing_account_id: str) -> list:
        try:
            api_version = "2019-10-01-preview"
            self.next_link = f"https://management.azure.com/providers/Microsoft.Billing/billingAccounts/{billing_account_id}/departments?api-version={api_version}"

            while self.next_link:
                url = self.next_link

                headers = self._make_request_headers(secret_data)
                response = requests.get(url=url, headers=headers)
                response_json = response.json()

                self.next_link = response_json.get("properties").get("nextLink", None)
                yield response_json
        except Exception as e:
            raise ERROR_UNKNOWN(message=f"[ERROR] list_departments {e}")

    def list_subscription(
        self,
        options: dict,
        secret_data: dict,
        agreement_type: str,
        billing_account_id: str,
    ) -> list:
        subscriptions = []

        if agreement_type == "EnterpriseAgreement":
            subscriptions = self.list_subscription_http(secret_data, billing_account_id)
        else:
            if sync_customers := options.get("sync_customers"):
                for customer_id in sync_customers:
                    customer_subscriptions = (
                        self.billing_client.billing_subscriptions.list_by_customer(
                            billing_account_name=billing_account_id,
                            api_version="2020-05-01",
                            customer_name=customer_id,
                        )
                    )
                    subscriptions.extend(customer_subscriptions)
            else:
                subscriptions = (
                    self.billing_client.billing_subscriptions.list_by_billing_account(
                        billing_account_name=billing_account_id,
                        api_version="2020-12-15-privatepreview",
                    )
                )
        return subscriptions

    def list_subscription_http(
        self, secret_data: dict, billing_account_id: str
    ) -> list:
        subscriptions = []
        try:
            api_version = "2022-10-01-privatepreview"
            self.next_link = f"https://management.azure.com/providers/Microsoft.Billing/billingAccounts/{billing_account_id}/billingSubscriptions?api-version={api_version}"

            while self.next_link:
                url = self.next_link

                headers = self._make_request_headers(secret_data)
                response = requests.get(url=url, headers=headers)
                response_json = response.json()
                response_value = response_json.get("value", [])

                self.next_link = response_json.get("nextLink", None)
                subscriptions.extend(response_value)
        except Exception as e:
            raise ERROR_UNKNOWN(message=f"[ERROR] list_subscription_http {e}")

        return subscriptions
