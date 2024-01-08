# Admin part of the bot. Interface for viewing active requests, current streram (specific case feature), PUSH notifications, settings (ability to change prices within the admin panel, start/stop recruitment
# (specific case feature), create groups and automatically add the bot as an admin). Implemented using aiogram and pyrogram with user sessions.

import asyncio
import logging

from pyrogram import Client
from pyrogram.raw.base import ChatAdminRights
from pyrogram.types import ChatPermissions, ChatPrivileges
from pyrogram.raw.functions.channels import EditAdmin

from filters.admin_filter import IsAdmin
from config.config import Config
from database import db
from keyboards import inline_keyboards

from aiogram.dispatcher.storage import FSMContext
from aiogram.utils.exceptions import ChatNotFound
from aiogram import Bot, Dispatcher
from aiogram import types

from states.bot_states import PUSH, SetPrice, CreateChannel, CreateGroup


async def setup_handlers(dp: Dispatcher, bot: Bot, bot_client: Client):
    @dp.message_handler(IsAdmin(), commands=["start"])
    async def start(message: types.Message):
        admin_id = message.from_user.id
        language_code = await db.get_language(admin_id)

        config_name = f'languages/{language_code}.ini'
        config = Config(user_id=admin_id, path=config_name)

        text = await config.get('ADMIN_MENU', 'text')
        keyboard = await inline_keyboards.admin_menu_keyboard(config, message.message_id)
        await message.answer(text, reply_markup=keyboard)

    @dp.message_handler(IsAdmin(), state='*', content_types=types.ContentType.ANY)
    async def process_message(message: types.Message, state: FSMContext):
        language_code = await db.get_language(message.from_user.id)
        if language_code is None:
            language_code = 'ua'
        config = Config(message.from_user.id, f"languages/{language_code}.ini")
        state = dp.current_state(chat=message.chat.id, user=message.from_user.id)
        current_state = await state.get_state()
        if current_state == "SetPrice:set_price_uah":
            async with state.proxy() as data:
                data['uah'] = int(message.text)
            await SetPrice.set_price_eur.set()

            current_value = await db.get_price(f'{data["type"]}_eur')
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goback'), callback_data="menu_settings"))

            text = (f"{await config.get('ADMIN_ACTIONS', 'set_price_eur')}\n\n"
                    f"{await config.get('ADMIN_ACTIONS', 'current_price_eur')}{current_value}")

            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            await bot.edit_message_text(chat_id=message.chat.id, message_id=data['message_id'], text=text,
                                        reply_markup=keyboard)

        elif current_state == "SetPrice:set_price_eur":
            async with state.proxy() as data:
                data['eur'] = int(message.text)

            await db.set_price(name=f"{data['type']}_uah", new_value=data['uah'])
            await db.set_price(name=f"{data['type']}_eur", new_value=data['eur'])

            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('GO_BACK', 'understood'),
                                           callback_data="menu_settings"))

            text = f"{await config.get('ADMIN_ACTIONS', 'success_price_change')}"

            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            await bot.edit_message_text(chat_id=message.chat.id, message_id=data['message_id'], text=text,
                                        reply_markup=keyboard)

        elif current_state == "CreateChannel:channel_name":
            async with state.proxy() as data:
                data["name"] = message.text
            await CreateChannel.channel_description.set()

            text = await config.get("CHANNEL", "channel_description")
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goprev'),
                                           callback_data="settings/additional"))

            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            await bot.edit_message_text(chat_id=message.chat.id, message_id=data['message_id'], text=text,
                                        reply_markup=keyboard)

        elif current_state == "CreateGroup:group_name":
            async with state.proxy() as data:
                data["name"] = message.text
            await CreateGroup.group_description.set()

            text = await config.get("CHANNEL", "group_description")
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goprev'),
                                           callback_data="settings/additional"))

            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            await bot.edit_message_text(chat_id=message.chat.id, message_id=data['message_id'], text=text,
                                        reply_markup=keyboard)

        elif current_state == "CreateChannel:channel_description":
            async with state.proxy() as data:
                data["description"] = message.text

            text = await config.get("CHANNEL", "channel_created")
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('GO_BACK', 'understood'),
                                           callback_data="settings/additional"))

            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            await bot.edit_message_text(chat_id=message.chat.id, message_id=data['message_id'], text=text,
                                        reply_markup=keyboard)

            channel = await bot_client.create_channel(title=data["name"], description=data["description"])
            info = await bot.get_me()
            await db.update_channel_data(channel.id)
            await bot_client.promote_chat_member(chat_id=channel.id, user_id=info.username,
                                                 privileges=ChatPrivileges(can_invite_users=True))

        elif current_state == "CreateGroup:group_description":
            async with state.proxy() as data:
                data["description"] = message.text

            text = await config.get("CHANNEL", "group_created")
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('GO_BACK', 'understood'),
                                           callback_data="settings/additional"))

            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            await bot.edit_message_text(chat_id=message.chat.id, message_id=data['message_id'], text=text,
                                        reply_markup=keyboard)

            group = await bot_client.create_supergroup(title=data["name"], description=data["description"])
            await db.update_group_data(group.id)
            info = await bot.get_me()
            await bot_client.promote_chat_member(chat_id=group.id, user_id=info.username,
                                                 privileges=ChatPrivileges(can_invite_users=True))

        elif current_state == "PUSH:add_message":
            async with state.proxy() as data:
                data["message"] = message

            text = await config.get("ADMIN_ACTIONS", "check")
            keyboard = types.InlineKeyboardMarkup(row_width=2)

            keyboard.add(types.InlineKeyboardButton(text=await config.get("ADMIN_ACTIONS", "send"), callback_data="send"),
                         types.InlineKeyboardButton(text=await config.get("ADMIN_ACTIONS", "repeat"), callback_data="repeat"))
            keyboard.add(types.InlineKeyboardButton(text=await config.get("GO_BACK", "goback"), callback_data="goback"))

            await message.answer(text=text, reply_markup=keyboard)

    @dp.callback_query_handler(IsAdmin(), state='*')
    async def process_callback_prev(callback_query: types.CallbackQuery, state: FSMContext):
        language_code = await db.get_language(callback_query.from_user.id)
        admin_id = callback_query.from_user.id

        if language_code is None:
            language_code = 'ua'
        config = Config(admin_id, f"languages/{language_code}.ini")

        if callback_query.data == "menu_invoices":
            keyboard = await inline_keyboards.request_keyboard(config)
            if keyboard is not None:
                text = await config.get("ADMIN_ACTIONS", "requests_text")
                keyboard.add(
                    types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goback'), callback_data="goback"))

                await callback_query.message.edit_text(text=text, reply_markup=keyboard)
            else:
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(
                    types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goback'), callback_data="goback"))

                text = await config.get("ADMIN_ACTIONS", "requests_text_none")

                await callback_query.message.edit_text(text=text, reply_markup=keyboard)

        elif callback_query.data.startswith("page_request/"):
            _, page = callback_query.data.split("/")
            keyboard = await inline_keyboards.request_keyboard(config, page=int(page))
            
            text = await config.get("ADMIN_ACTIONS", "requests_text")
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goback'), callback_data="goback"))

            await callback_query.message.edit_text(text=text, reply_markup=keyboard)

        elif callback_query.data == "menu_all_payed":
            count = await db.kino_count()
            keyboard = await inline_keyboards.accepted_keyboard(config)
            if keyboard is not None:
                text = f'{await config.get("ADMIN_ACTIONS", "accepted_text")}\n\n{await config.get("ADMIN_ACTIONS", "kino_statistic")}{count}'
                keyboard.add(
                    types.InlineKeyboardButton(text=await config.get('ADMIN_ACTIONS', 'invite'),
                                               callback_data="invite"))
                keyboard.add(
                    types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goback'), callback_data="goback"))

                await callback_query.message.edit_text(text=text, reply_markup=keyboard)
            else:
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(
                    types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goback'), callback_data="goback"))

                text = await config.get("ADMIN_ACTIONS", "accepted_text_none")

                await callback_query.message.edit_text(text=text, reply_markup=keyboard)

        elif callback_query.data.startswith("page_payed/"):
            _, page = callback_query.data.split("/")
            count = await db.kino_count()
            keyboard = await inline_keyboards.accepted_keyboard(config, page=int(page))
            
            text = f'{await config.get("ADMIN_ACTIONS", "accepted_text")}\n\n{await config.get("ADMIN_ACTIONS", "kino_statistic")}{count}'
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('ADMIN_ACTIONS', 'invite'),
                                            callback_data="invite"))
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goback'), callback_data="goback"))

            await callback_query.message.edit_text(text=text, reply_markup=keyboard)

        elif callback_query.data.startswith("request/"):
            user_id = callback_query.data.split('/')[1]
            info = await db.get_info_about_invoice(int(user_id))
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('ADMIN_ACTIONS', 'accept'),
                                           callback_data=f"accept/{user_id}"),
                types.InlineKeyboardButton(text=await config.get('ADMIN_ACTIONS', 'decline'),
                                           callback_data=f"decline/{user_id}"))
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goprev'), callback_data="menu_invoices"))

            info_dict = {
                "personal": await config.get("ADMIN_ACTIONS", "info_dict_personal"),
                "simple": await config.get("ADMIN_ACTIONS", "info_dict_simple")
            }

            text = (f"{await config.get('ADMIN_ACTIONS', 'info_text_id')}{info[0]}\n"
                    f"{await config.get('ADMIN_ACTIONS', 'info_text_tag')}@{info[1]}\n"
                    f"{await config.get('ADMIN_ACTIONS', 'info_text_type')}{info_dict[info[2]]}\n"
                    f"<a href='{info[3]}'>{await config.get('ADMIN_ACTIONS', 'info_text_screenshot')}</a>")

            await callback_query.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")

        elif callback_query.data.startswith("accept/"):
            user_id = callback_query.data.split('/')[1]
            await db.change_processed(user_id=int(user_id), processed=1)

            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goprev'), callback_data="menu_invoices"))

            text = await config.get("ADMIN_ACTIONS", "user_accepted_text")

            await callback_query.message.edit_text(text=text, reply_markup=keyboard)

        elif callback_query.data.startswith("decline/"):
            user_id = callback_query.data.split('/')[1]
            await db.change_processed(user_id=int(user_id), processed=2)

            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goprev'), callback_data="menu_invoices"))

            text = await config.get("ADMIN_ACTIONS", "user_declined_text")

            await callback_query.message.edit_text(text=text, reply_markup=keyboard)

        elif callback_query.data.startswith("payed/"):
            user_id = callback_query.data.split('/')[1]
            info = await db.get_info_about_invoice(int(user_id))
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goprev'), callback_data="menu_all_payed"))

            info_dict = {
                "personal": await config.get("ADMIN_ACTIONS", "info_dict_personal"),
                "simple": await config.get("ADMIN_ACTIONS", "info_dict_simple"),
                0: await config.get("ADMIN_ACTIONS", "yes"),
                1: await config.get("ADMIN_ACTIONS", "no")
            }

            text = (f"{await config.get('ADMIN_ACTIONS', 'info_text_id')}{info[0]}\n"
                    f"{await config.get('ADMIN_ACTIONS', 'info_text_tag')}@{info[1]}\n"
                    f"{await config.get('ADMIN_ACTIONS', 'info_text_type')}{info_dict[info[2]]}\n"
                    f"{await config.get('ADMIN_ACTIONS', 'info_text_invited')}{info_dict[info[4]]}\n"
                    f"<a href='{info[3]}'>{await config.get('ADMIN_ACTIONS', 'info_text_screenshot')}</a>")

            await callback_query.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")

        elif callback_query.data == "invite":
            group_id, channel_id = await db.get_channel_data()
            users = await db.get_not_invited()
            if group_id and channel_id:
                for user in users:
                    try:
                        group_link = await bot_client.create_chat_invite_link(chat_id=group_id, member_limit=1)
                        channel_link = await bot_client.create_chat_invite_link(chat_id=channel_id, member_limit=1)

                        text = (f"{await config.get('ADMIN_ACTIONS', 'link_into_channel')}{channel_link.invite_link}\n"
                                f"{await config.get('ADMIN_ACTIONS', 'link_into_group')}{group_link.invite_link}")
                        keyboard = types.InlineKeyboardMarkup()
                        keyboard.add(types.InlineKeyboardButton(text=await config.get("GO_BACK", "understood"),
                                                                callback_data="delete"))

                        await bot.send_message(chat_id=user, text=text, reply_markup=keyboard)
                        await db.change_invited(user_id=user)
                    except ChatNotFound:
                        pass

                text = await config.get('ADMIN_ACTIONS', 'link_sent')
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton(text=await config.get("GO_BACK", "goprev"),
                                                        callback_data="menu_all_payed"))

                await callback_query.message.edit_text(text=text, reply_markup=keyboard)
            else:

                text = await config.get('ADMIN_ACTIONS', 'groups_error')
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton(text=await config.get("GO_BACK", "goprev"),
                                                        callback_data="menu_all_payed"))

                await callback_query.message.edit_text(text=text, reply_markup=keyboard)

        elif callback_query.data == "menu_poetry":
            keyboard = await inline_keyboards.poetry_keyboard(config)
            count = await db.poetry_count()
            if keyboard is not None:
                text = f'{await config.get("ADMIN_ACTIONS", "poetry_request_text")}\n\n{await config.get("ADMIN_ACTIONS", "poetry_statistic")}{count}'
                keyboard.add(
                    types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goback'), callback_data="goback"))

                await callback_query.message.edit_text(text=text, reply_markup=keyboard)
            else:
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(
                    types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goback'), callback_data="goback"))

                text = f'{await config.get("ADMIN_ACTIONS", "poetry_request_text_none")}\n\n{await config.get("ADMIN_ACTIONS", "poetry_statistic")}{count}'
                await callback_query.message.edit_text(text=text, reply_markup=keyboard)

        elif callback_query.data.startswith("poetry_request"):
            user_id = callback_query.data.split('/')[1]
            info = await db.get_info_about_poetry_invoice(int(user_id))
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('ADMIN_ACTIONS', 'accept'),
                                           callback_data=f"poetry_accept/{user_id}"),
                types.InlineKeyboardButton(text=await config.get('ADMIN_ACTIONS', 'decline'),
                                           callback_data=f"poetry_decline/{user_id}"))
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goprev'), callback_data="menu_poetry"))

            text = (f"{await config.get('ADMIN_ACTIONS', 'info_text_id')}{info[0]}\n"
                    f"{await config.get('ADMIN_ACTIONS', 'info_text_tag')}@{info[1]}\n"
                    f"<a href='{info[2]}'>{await config.get('ADMIN_ACTIONS', 'info_text_screenshot')}</a>")

            await callback_query.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")

        elif callback_query.data.startswith("poetry_accept/"):
            user_id = callback_query.data.split('/')[1]
            await db.change_poetry_processed(user_id=int(user_id), processed=1)

            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goprev'), callback_data="menu_poetry"))

            text = await config.get("ADMIN_ACTIONS", "user_poetry_accepted_text")

            await callback_query.message.edit_text(text=text, reply_markup=keyboard)

            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('GO_BACK', 'thanks'), callback_data="goback_buy"))

            with open('static/«Регенерація».pdf', 'rb') as document:
                await bot.send_document(chat_id=user_id, document=document, caption=await config.get('ADMIN_ACTIONS', 'thank_you_user'), reply_markup=keyboard, parse_mode="HTML")

        elif callback_query.data.startswith("poetry_decline/"):
            user_id = callback_query.data.split('/')[1]
            await db.change_poetry_processed(user_id=int(user_id), processed=2)

            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goprev'), callback_data="menu_poetry"))

            text = await config.get("ADMIN_ACTIONS", "user_declined_text")

            await callback_query.message.edit_text(text=text, reply_markup=keyboard)

        elif callback_query.data == "menu_settings":
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('ADMIN_ACTIONS', 'settings_menu_poetry'),
                                           callback_data="settings/poetry"),
                types.InlineKeyboardButton(text=await config.get('ADMIN_ACTIONS', 'settings_menu_kino'),
                                           callback_data="settings/kino"),
                types.InlineKeyboardButton(text=await config.get('ADMIN_ACTIONS', 'settings_menu_additional'),
                                           callback_data="settings/additional")
            )
            keyboard.add(types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goback'), callback_data="goback"))

            text = await config.get('ADMIN_ACTIONS', 'settings_menu_choose')

            await callback_query.message.edit_text(text=text, reply_markup=keyboard)

        elif callback_query.data.startswith("settings/"):
            if callback_query.data == "settings/poetry":
                keyboard = types.InlineKeyboardMarkup(row_width=2)
                keyboard.add(types.InlineKeyboardButton(text=await config.get('ADMIN_ACTIONS', 'change_price_poetry'),
                                                        callback_data="price_regeneration"))
                keyboard.add(types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goprev'),
                                                        callback_data="menu_settings"))

                text = await config.get('ADMIN_ACTIONS', 'settings_menu_avalible')

                await callback_query.message.edit_text(text=text, reply_markup=keyboard)

            elif callback_query.data == "settings/kino":
                keyboard = types.InlineKeyboardMarkup(row_width=2)
                keyboard.add(
                    types.InlineKeyboardButton(text=await config.get('ADMIN_ACTIONS', 'change_price_kino_simple'),
                                               callback_data="price_simple"),
                    types.InlineKeyboardButton(text=await config.get('ADMIN_ACTIONS', 'change_price_kino_personal'),
                                               callback_data="price_personal"))
                keyboard.add(types.InlineKeyboardButton(text=await config.get('ADMIN_ACTIONS', 'change_kino_status'),
                                                        callback_data="status_kino"))
                keyboard.add(types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goprev'),
                                                        callback_data="menu_settings"))

                text = await config.get('ADMIN_ACTIONS', 'settings_menu_avalible')

                await callback_query.message.edit_text(text=text, reply_markup=keyboard)

            elif callback_query.data == "settings/additional":
                keyboard = types.InlineKeyboardMarkup(row_width=2)
                keyboard.add(
                    types.InlineKeyboardButton(text=await config.get('ADMIN_ACTIONS', 'create_group'),
                                               callback_data="create_group"),
                    types.InlineKeyboardButton(text=await config.get('ADMIN_ACTIONS', 'create_channel'),
                                               callback_data="create_channel"))
                keyboard.add(types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goprev'),
                                                        callback_data="menu_settings"))

                text = await config.get('ADMIN_ACTIONS', 'settings_menu_avalible')

                await callback_query.message.edit_text(text=text, reply_markup=keyboard)

        elif callback_query.data == "create_group":
            await CreateGroup.group_name.set()
            async with state.proxy() as data:
                data["message_id"] = callback_query.message.message_id

            text = await config.get("CHANNEL", "group_name")
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(text=await config.get("GO_BACK", "goprev"),
                                                    callback_data="settings/additional"))

            await callback_query.message.edit_text(text=text, reply_markup=keyboard)

        elif callback_query.data == "create_channel":
            await CreateChannel.channel_name.set()
            async with state.proxy() as data:
                data["message_id"] = callback_query.message.message_id

            text = await config.get("CHANNEL", "channel_name")
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(text=await config.get("GO_BACK", "goprev"),
                                                    callback_data="settings/additional"))

            await callback_query.message.edit_text(text=text, reply_markup=keyboard)

        elif callback_query.data.startswith("price_"):
            await SetPrice.set_price_uah.set()
            async with state.proxy() as data:
                data['type'] = callback_query.data.split("_")[1]
            current_value = await db.get_price(f'{data["type"]}_uah')
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goback'), callback_data="menu_settings"))

            text = (f"{await config.get('ADMIN_ACTIONS', 'set_price_uah')}\n\n"
                    f"{await config.get('ADMIN_ACTIONS', 'current_price_uah')}{current_value} UAH")

            await callback_query.message.edit_text(text=text, reply_markup=keyboard)
            async with state.proxy() as data:
                data['message_id'] = callback_query.message.message_id

        elif callback_query.data == 'status_kino':
            current_status = await db.get_is_active()
            info_dict = {
                0: await config.get('ADMIN_ACTIONS', 'inactive'),
                1: await config.get('ADMIN_ACTIONS', 'active')
            }
            text = (f"{await config.get('ADMIN_ACTIONS', 'status_kino_text')}\n\n"
                    f"{await config.get('ADMIN_ACTIONS', 'status_kino_current')}{info_dict[current_status]}")
            button_text = await config.get('ADMIN_ACTIONS', 'button_text')

            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(text=button_text, callback_data=f"change_status/{current_status}"))
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goprev'), callback_data="menu_settings"))

            await callback_query.message.edit_text(text=text, reply_markup=keyboard)

        elif callback_query.data.startswith("change_status/"):
            status = callback_query.data.split("/")[1]
            if status == "0":
                text = await config.get('ADMIN_ACTIONS', 'activated')

                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goprev'),
                                                        callback_data="menu_settings"))

                await callback_query.message.edit_text(text=text, reply_markup=keyboard)

                user_list = await db.is_user()
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(
                    types.InlineKeyboardButton(text=await config.get("GO_BACK", "understood"), callback_data='delete'))

                text = await config.get("KINO", "kino_activated")

                for user in user_list:
                    try:
                        await bot.send_message(chat_id=user, text=text, reply_markup=keyboard, parse_mode="HTML")
                    except:
                        await asyncio.sleep(1)

                channel_id, group_id = await db.get_channel_data()
                info = await bot.get_me()
                try:
                    await bot_client.ban_chat_member(chat_id=int(channel_id), user_id=info.username)
                    await bot_client.ban_chat_member(chat_id=int(group_id), user_id=info.username)
                except Exception as e:
                    logging.info(e)

                await db.set_is_active()

            else:
                await db.set_is_active()
                text = await config.get('ADMIN_ACTIONS', 'deactivated')

                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(
                    types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goprev'),
                                               callback_data="menu_settings"))

                await callback_query.message.edit_text(text=text, reply_markup=keyboard)

                user_list = await db.is_user()
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(
                    types.InlineKeyboardButton(text=await config.get("GO_BACK", "understood"), callback_data='delete'))

                text = await config.get("KINO", "kino_inactive")

                for user in user_list:
                    try:
                        await bot.send_message(chat_id=user, text=text, reply_markup=keyboard, parse_mode="HTML")
                    except:
                        await asyncio.sleep(1)

        elif callback_query.data == "call_back":
            text = await config.get("ADMIN_ACTIONS", "call_back")
            keyboard = await inline_keyboards.call_back_keyboard(config)

            if keyboard:
                await callback_query.message.edit_text(text=text, reply_markup=keyboard)
            else:
                text = await config.get("ADMIN_ACTIONS", "call_back_none")
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(
                    types.InlineKeyboardButton(text=await config.get("GO_BACK", "goback"), callback_data="goback"))

                await callback_query.message.edit_text(text=text, reply_markup=keyboard)

        elif callback_query.data.startswith("page_cb/"):
            _, page = callback_query.data.split("/")
            keyboard = await inline_keyboards.call_back_keyboard(config, page=int(page))
            text = await config.get("ADMIN_ACTIONS", "call_back")
            await callback_query.message.edit_text(text=text, reply_markup=keyboard)

        elif callback_query.data.startswith("cb/"):
            user_id = callback_query.data.split('/')[1]
            info = await db.get_info_about_invoice(int(user_id))
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goprev'), callback_data="call_back"))

            info_dict = {
                "personal": await config.get("ADMIN_ACTIONS", "info_dict_personal"),
                "simple": await config.get("ADMIN_ACTIONS", "info_dict_simple"),
                0: await config.get("ADMIN_ACTIONS", "yes"),
                1: await config.get("ADMIN_ACTIONS", "no")
            }

            text = (f"{await config.get('ADMIN_ACTIONS', 'info_text_id')}{info[0]}\n"
                    f"{await config.get('ADMIN_ACTIONS', 'info_text_tag')}@{info[1]}\n"
                    f"{await config.get('ADMIN_ACTIONS', 'info_text_type')}{info_dict[info[2]]}\n"
                    f"{await config.get('ADMIN_ACTIONS', 'info_text_invited')}{info_dict[info[4]]}\n"
                    f"<a href='{info[3]}'>{await config.get('ADMIN_ACTIONS', 'info_text_screenshot')}</a>")

            await callback_query.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")

        elif callback_query.data == "menu_push":
            await PUSH.add_message.set()
            async with state.proxy() as data:
                data["message_id"] = int(callback_query.message.message_id)

            text = await config.get("ADMIN_ACTIONS", "push")
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(text=await config.get("GO_BACK", "goback"), callback_data="goback"))

            await callback_query.message.edit_text(text=text, reply_markup=keyboard)

        elif callback_query.data == "repeat":
            data = await state.get_data()
            await PUSH.add_message.set()

            text = await config.get("ADMIN_ACTIONS", "push")
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(text=await config.get("GO_BACK", "goback"), callback_data="goback"))

            await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=data["message_id"])
            await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=data["message"].message_id)

            await callback_query.message.edit_text(text=text, reply_markup=keyboard)

        elif callback_query.data == "send":
            user_list = await db.is_user()
            data = await state.get_data()
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get("GO_BACK", "understood"), callback_data='delete'))

            for user in user_list:
                try:
                    await bot.copy_message(from_chat_id=callback_query.message.chat.id, chat_id=user,
                                           message_id=data["message"].message_id, reply_markup=keyboard,
                                           parse_mode="HTML")
                except:
                    await asyncio.sleep(1)

            text = await config.get("ADMIN_ACTIONS", "ready")
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get("GO_BACK", "goback"), callback_data='goback'))

            await callback_query.message.edit_text(text=text, reply_markup=keyboard)

        elif callback_query.data == 'goback':
            text = await config.get('ADMIN_MENU', 'text')
            keyboard = await inline_keyboards.admin_menu_keyboard(config, callback_query.message.message_id)

            await callback_query.message.edit_text(text, reply_markup=keyboard)
            await state.finish()

        elif callback_query.data == 'delete':
            await bot.delete_message(chat_id=callback_query.message.chat.id,
                                     message_id=callback_query.message.message_id)
