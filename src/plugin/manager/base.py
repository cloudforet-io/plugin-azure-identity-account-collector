import logging

from spaceone.core.manager import BaseManager

_LOGGER = logging.getLogger("spaceone")


class AzureBaseManager(BaseManager):
    provider = "azure"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.resource_client = None

    def sync(
        self, options: dict, secret_data: dict, domain_id: str, schema_id: str = None
    ) -> list:
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

    @classmethod
    def get_all_managers(cls, options) -> list:
        return cls.__subclasses__()
