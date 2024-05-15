import logging

from spaceone.identity.plugin.account_collector.lib.server import (
    AccountCollectorPluginServer,
)
from plugin.manager.base import AzureBaseManager

_LOGGER = logging.getLogger("spaceone")

app = AccountCollectorPluginServer()


@app.route("AccountCollector.init")
def account_collector_init(params: dict) -> dict:
    """init plugin by options

    Args:
        params (CollectorInitRequest): {
            'options': 'dict',    # Required
            'domain_id': 'str'
        }

    Returns:
        PluginResponse: {
            'metadata': 'dict'
        }
    """

    options = params.get("options", {}) or {}

    metadata = {
        "additional_options_schema": {
            "type": "object",
            "properties": {
                "exclude_root_management_group": {
                    "title": "Exclude Tenant Root Group",
                    "type": "boolean",
                    "default": True,
                },
                "sync_customers": {
                    "title": "Sync Customers",
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [],
                    "description": "Only can use MicrosoftPartnerAgreement. If empty, all customers will be synced.",
                },
            },
        }
    }

    additional_options_schema = metadata["additional_options_schema"]

    if exclude_root_management_group := options.get("exclude_root_management_group"):
        additional_options_schema["properties"]["exclude_root_management_group"][
            "default"
        ] = exclude_root_management_group

    if sync_customers := options.get("sync_customers"):
        additional_options_schema["properties"]["sync_customers"][
            "default"
        ] = sync_customers

    metadata["additional_options_schema"] = additional_options_schema
    return {"metadata": metadata}


@app.route("AccountCollector.sync")
def account_collector_sync(params: dict) -> dict:
    """AccountCollector sync

    Args:
        params (AccountCollectorInit): {
            'options': 'dict',          # Required
            'schema_id': 'str',
            'secret_data': 'dict',      # Required
            'domain_id': 'str'          # Required
        }

    Returns:
        AccountsResponse:
        {
            'results': [
                {
                    name: 'str',
                    data: 'dict',
                    secret_schema_id: 'str',
                    secret_data: 'dict',
                    tags: 'dict',
                    location: 'list'
                }
            ]
        }
    """

    secret_data = params["secret_data"]
    schema_id = params.get("schema_id")
    options = params["options"]
    domain_id = params["domain_id"]

    results = []
    billing_accounts = AzureBaseManager.list_billing_accounts(secret_data)

    for billing_account in billing_accounts:
        agreement_type = _get_agreement_type(billing_account)
        billing_account_id = billing_account.name or None

        account_collector_manager = AzureBaseManager.get_manager_by_agreement_type(
            agreement_type
        )
        ac_mgr = account_collector_manager()
        results.extend(
            ac_mgr.sync(
                options=options,
                secret_data=secret_data,
                domain_id=domain_id,
                billing_account_id=billing_account_id,
                schema_id=schema_id,
            )
        )
    if not billing_accounts:
        account_collector_manager = AzureBaseManager.get_manager_by_agreement_type(
            "Unknown"
        )
        ac_mgr = account_collector_manager()
        results.extend(
            ac_mgr.sync(
                options=options,
                secret_data=secret_data,
                domain_id=domain_id,
                schema_id=schema_id,
            )
        )

    return {"results": results}


def _get_agreement_type(billing_account) -> str:
    agreement_type = "Unknown"
    try:
        agreement_type = billing_account.agreement_type
    except Exception as e:
        _LOGGER.debug(f"Failed to get agreement_type: {e}")

    return agreement_type
