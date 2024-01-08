# Message distribution filter for users

from aiogram.types import Message
from aiogram.dispatcher.filters import BoundFilter
from database import db


class IsUser(BoundFilter):
    async def check(self, message: Message):
        if not await db.is_profiled(int(message.from_user.id)):
            return True

        user_list = await db.is_user()
        return int(message.from_user.id) in user_list

