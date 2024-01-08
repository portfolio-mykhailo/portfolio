import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config.config import Config
from pyrogram import Client
from aiogram.types import Update

from database import db
from handlers.admin import admin
from handlers.user import user

logging.basicConfig(level=logging.INFO)


class AiogramInstance:
    dispatcher_instance = None
    bot_instance = None

    @staticmethod
    async def get_instance():
        config = Config(1, "config.ini")
        if AiogramInstance.dispatcher_instance is None:
            token = await config.get('BOT_TOKEN', 'token')
            bot = Bot(token=token)
            AiogramInstance.dispatcher_instance = Dispatcher(bot, storage=MemoryStorage())
            AiogramInstance.bot_instance = bot
        return [AiogramInstance.dispatcher_instance, AiogramInstance.bot_instance]


class PyrogramInstance:
    bot_instance = None

    @staticmethod
    async def get_instance():
        config = Config(1, "config.ini")
        if PyrogramInstance.bot_instance is None:
            api_id = await config.get('BOT_TOKEN', 'api_id')
            api_hash = await config.get('BOT_TOKEN', 'api_hash')
            session_file_name = await config.get('BOT_TOKEN', 'session_file_name')
            client = Client(session_file_name, api_id=api_id, api_hash=api_hash)
            PyrogramInstance.bot_instance = client
        return PyrogramInstance.bot_instance
    

async def startup():
    await db.start_db()

    instance_list = await AiogramInstance.get_instance()
    dp, bot = instance_list
    print('Aiogram started')

    bot_client = await PyrogramInstance.get_instance()
    print('Pyrogram started')

    await asyncio.gather(dp.start_polling(), bot_client.start(), user.setup_handlers(dp, bot), admin.setup_handlers(dp, bot, bot_client))


async def main():
    await startup()


if __name__ == '__main__':
    asyncio.run(main())
