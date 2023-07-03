import abc
from fake_useragent import UserAgent
from typing import Union, Dict

USER_AGENT = UserAgent().chrome


class AbstractService(abc.ABC):
    SERVICE_DEFAULT_CONFIG: Union[None, Dict[str, Union[str, int, bool]]]
    SERVICE_NAME: str
    SERVICE_LABEL: str
    SERVICE_COLOR: int

    @abc.abstractmethod
    async def standardize_url(self, url: str) -> Union[str, None]:
        raise NotImplementedError

    @abc.abstractmethod
    async def fetch_items(self, url_list: list):
        raise NotImplementedError

    @abc.abstractmethod
    async def get_product_info(self, url: str):
        raise NotImplementedError


class BaseServiceItem:
    """Base class for service items."""
    def __init__(self, item_dict: dict, **kwargs):
        self.dict = item_dict

        for key, value in kwargs.items():
            self.__setitem__(key, value)

    def label(self, key):
        return self.dict[key]['label']

    def type(self, key):
        return self.dict[key]['type']

    def value(self, key):
        return self.dict[key]['value']

    def __iter__(self):
        return iter(self.dict)

    def __len__(self):
        return len(self.dict)

    def keys(self):
        return self.dict.keys()

    def values(self):
        return self.dict.values()

    def items(self):
        return self.dict.items()

    def __getitem__(self, key) -> Union[str, int]:
        return self.dict[key]['value']

    def __setitem__(self, key, value) -> None:
        if type(value) is not self.dict[key]['type']:
            raise TypeError(f'{key} value type must be {self.dict[key]["type"]}, not {type(value)}')
        elif key not in self.dict.keys():
            raise KeyError(f'{key} is not a valid key for {self.__class__.__name__}')
        else:
            self.dict[key]['value'] = value

    def __repr__(self):
        return str(self.dict)

    def __eq__(self, other):
        return self.dict == other.dict
