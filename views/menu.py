import discord  # noqa
from typing import Callable, Dict, Any, List
from views.add import AddModal
from views.selector import ItemSelectorView
from services.base import AbstractService, BaseServiceItem
from util.embed_factory import get_embed


class MenuView(discord.ui.View):
    def __init__(self, services: Dict[str, AbstractService], item_dict: Dict[str, Dict[str, BaseServiceItem]],
                 add_callback: Callable[[discord.Interaction, str], Any],
                 list_callback: Callable[[discord.Interaction], Any],
                 info_callback: Callable[[discord.Interaction, str, str], Any],
                 delete_callback: Callable[[discord.Interaction, str, List[str]], Any],
                 cancel_callback: Callable[[discord.Interaction], Any]):
        """Menu button view. All callbacks must be async functions.
        :param item_dict: 상품 딕셔너리
        :param add_callback: 추가 모달 콜백 (Interaction, url)
        :param list_callback: 상품 목록 콜백 (Interaction)
        :param info_callback: 상품 정보 확인 콜백 (Interaction, 서비스 명, url)
        :param delete_callback: 상품 삭제 콜백 (Interaction, 서비스 명, url 리스트)
        """
        super().__init__(timeout=None)
        self.services = services
        self.add_callback = add_callback
        self.list_callback = list_callback
        self.info_callback = info_callback
        self.delete_callback = delete_callback
        self.cancel_callback = cancel_callback
        self.item_dict = item_dict

    @discord.ui.button(label="추가", row=0, style=discord.ButtonStyle.green)
    async def first_button_callback(self, _, interaction):
        await interaction.response.send_modal(AddModal(self, self.add_callback))

    @discord.ui.button(label="상품 목록", row=0, style=discord.ButtonStyle.primary)
    async def second_button_callback(self, _, interaction):
        await self.list_callback(interaction)

    @discord.ui.button(label="상품 정보 보기", row=0, style=discord.ButtonStyle.primary)
    async def third_button_callback(self, _, interaction):
        for service_dict in self.item_dict.values():
            if service_dict:
                break
        else:
            await interaction.response.edit_message(
                embed=get_embed(title='상품 정보 보기', description='추가된 상품이 없습니다.')
            )
            return
        await interaction.response.edit_message(
            embed=get_embed(title='상품 정보 보기', description='정보를 볼 상품을 선택하세요.'),
            view=ItemSelectorView(self.services, self.item_dict, self.info_callback, self.cancel_callback)
        )

    @discord.ui.button(label="삭제", row=0, style=discord.ButtonStyle.danger)
    async def fourth_button_callback(self, _, interaction):
        for service_dict in self.item_dict.values():
            if service_dict:
                break
        else:
            await interaction.response.edit_message(
                embed=get_embed(title='상품 삭제', description='추가된 상품이 없습니다.')
            )
            return
        await interaction.response.edit_message(
            embed=get_embed(title='상품 삭제', description='삭제할 상품을 선택하세요.'),
            view=ItemSelectorView(self.services, self.item_dict, self.delete_callback, self.cancel_callback, select_multiple=True)
        )
