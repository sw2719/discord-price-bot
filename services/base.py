import abc
from typing import Union

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'


class AbstractService(abc.ABC):
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
