import abc
from typing import Union


class BaseService(abc.ABC):
    @abc.abstractmethod
    def standardize_url(self, url: str) -> Union[str, None]:
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_items(self, url_list: list):
        raise NotImplementedError

    @abc.abstractmethod
    def get_product_info(self, url: str):
        raise NotImplementedError


class BaseServiceItem:
    """Base class for service items."""
    def __init__(self, override_dict: dict = None):
        if override_dict is None:
            self.dict = {
                'name': {'label': '상품명', 'type': str, 'value': ''},
                'option': {'type': dict, 'value': {}},
                'price': {'label': '가격', 'type': int, 'value': 0},
                'thumbnail': {'type': str, 'value': ''}
            }

        else:
            self.dict = override_dict
            if not set(self.dict).issubset(set(override_dict)):
                missing_keys = set(self.dict).difference(set(override_dict))
                raise KeyError(f'{str(missing_keys)} is missing from override_dict')

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
            raise TypeError(f'{key} value type must be {self.dict[key]["type"]}')
        elif key not in self.dict.keys():
            raise KeyError(f'{key} is not a valid key for {self.__class__.__name__}')
        else:
            self.dict[key]['value'] = value

    def __repr__(self):
        return str(self.dict)
