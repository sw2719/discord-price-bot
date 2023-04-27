import discord  # noqa


class AddModal(discord.ui.Modal):
    """Input Modal for adding item via URL or recommendation link (for applicable services)"""
    def __init__(self, view: discord.ui.View, callback, *args, **kwargs):
        super().__init__(title='상품 추가', *args, **kwargs)
        self.view = view

        self.add_item(discord.ui.InputText(label="추가할 상품의 URL 또는 추천 URL/문구를 입력하세요.",
                                           style=discord.InputTextStyle.long))
        self.callback_ = callback

    async def callback(self, interaction: discord.Interaction):
        await self.callback_(interaction, self.children[0].value)
