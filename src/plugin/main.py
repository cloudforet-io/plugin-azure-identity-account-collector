from spaceone.identity.plugin.account_collector.lib.server import (
    AccountCollectorPluginServer,
)
from plugin.manager.base import AzureBaseManager

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
            },
        }
    }

    if exclude_root_management_group := options.get("exclude_root_management_group"):
        metadata["additional_options_schema"]["properties"][
            "exclude_root_management_group"
        ]["default"] = exclude_root_management_group

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
    for account_collector_manager in AzureBaseManager.get_all_managers(options={}):
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
