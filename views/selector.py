import discord  # noqa
import asyncio
from typing import Callable, Dict, List

from services.base import AbstractService, BaseServiceItem


class ItemSelector(discord.ui.Select):
    def __init__(self, service_name: str, options: List[discord.SelectOption], callback: Callable, select_multiple):
        if select_multiple:
            max_values = len(options)
        else:
            max_values = 1

        super().__init__(
            placeholder='상품을 선택하세요...',
            min_values=1,
            max_values=max_values,
            options=options
        )

        self.service = service_name
        self._callback = callback

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.view.clear_items()
        await interaction.edit_original_response(view=self.view)

        if self.view.select_multiple:
            await self._callback(interaction, self.service, self.values)
        else:
            selected_item_url = self.values[0]
            await self._callback(interaction, self.service, selected_item_url)


class ServiceSelector(discord.ui.Select):
    def __init__(self, services: Dict[str, AbstractService], item_dict: Dict[str, Dict[str, BaseServiceItem]], options: List[discord.SelectOption]):
        self.item_dict = item_dict

        if len(options) == 1:
            options[0].default = True
            disabled = True
        else:
            disabled = False

        super().__init__(
            placeholder="서비스를 선택하세요...",
            min_values=1,
            max_values=1,
            options=options,
            disabled=disabled
        )

    async def callback(self, interaction: discord.Interaction):
        service = self.values[0]
        for option in self.options:
            if option.value == service:
                option.default = True
            else:
                option.default = False

        self.view.add_item_selector(service, self.item_dict[service])
        await interaction.response.defer()
        await interaction.edit_original_response(view=self.view)


class ItemSelectorView(discord.ui.View):
    def __init__(self, services: Dict[str, AbstractService], item_dict: Dict[str, Dict[str, BaseServiceItem]],
                 callback: Callable, cancel_callback: Callable, select_multiple: bool = False):
        """"""
        super().__init__()
        self._callback = callback
        self._cancel_callback = cancel_callback
        self.item_selector_added = False
        self.item_selector = None
        self.select_multiple = select_multiple

        options = [discord.SelectOption(label=services[service_name].SERVICE_LABEL,
                                        value=services[service_name].SERVICE_NAME,
                                        description=f'{len(items)}개 추가됨')
                   for service_name, items in item_dict.items() if items]

        service_selector = ServiceSelector(services, item_dict, options)
        self.add_item(service_selector)

        if len(options) == 1:
            self.add_item_selector(options[0].value, item_dict[options[0].value])

    @discord.ui.button(label="취소", row=4, style=discord.ButtonStyle.primary)
    async def first_button_callback(self, _, interaction):
        await interaction.response.defer()
        await self._cancel_callback(interaction)

    def add_item_selector(self, service_name, service_dict: Dict[str, BaseServiceItem]):
        if self.item_selector_added:
            self.remove_item(self.item_selector)
        else:
            self.item_selector_added = True

        options = []
        for url, item in service_dict.items():
            label = item['name']
            item_options_lines = []
            try:
                item_options = item['option']

                for key, value in item_options.items():
                    item_options_lines.append(f"{key}: {value}")

            except KeyError:
                pass

            while True:
                item_options_string = '\n'.join(item_options_lines)

                if len(item_options_string) < 100:
                    break
                else:
                    item_options_lines.pop()

            if len(label) > 100:
                label = label[:97] + '...'

            options.append(discord.SelectOption(label=label, value=url, description=item_options_string))

        self.item_selector = ItemSelector(service_name, options, self._callback, self.select_multiple)
        self.add_item(self.item_selector)
