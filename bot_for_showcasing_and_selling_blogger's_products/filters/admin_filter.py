# Message distribution filter for admins

from aiogram.types import Message
from aiogram.dispatcher.filters import BoundFilter
from database import db


class IsAdmin(BoundFilter):
    async def check(self, message: Message):
        admins_list = await db.is_admin()

        return int(message.from_user.id) in admins_list
