# User-facing part of the bot. What the user sees and the processing of individual user operations
# (e.g., sending a screenshot of payment for a particular service).

from aiogram.utils.exceptions import BadRequest
from aiogram.dispatcher import FSMContext

from utils import telepraph
from filters.user_filter import IsUser
from database import db
from keyboards import inline_keyboards
from config.config import Config
from states.bot_states import SendScreenshot

from aiogram import Bot, Dispatcher
from aiogram import types


async def setup_handlers(dp: Dispatcher, bot: Bot):
    @dp.message_handler(IsUser(), commands=["start"])
    async def start(message: types.Message):
        user_id = message.from_user.id
        is_profiled = await db.is_profiled(user_id)
        if is_profiled:
            language_code = await db.get_language(user_id)

            config_name = f'languages/{language_code}.ini'
            config = Config(user_id=user_id, path=config_name)

            text = await config.get("USER", "user_start")
            keyboard = await inline_keyboards.main_menu_keyboard(config)

            await message.answer(text=text, reply_markup=keyboard, parse_mode="HTML")

        else:
            language_code = 'ua'
            config = Config(message.from_user.id, f"languages/{language_code}.ini")
            await db.add_to_db(user_id=user_id, tag=message.from_user.username,
                               name=message.from_user.first_name, language=language_code, admin=0)

            text = await config.get("USER", "user_start")
            keyboard = await inline_keyboards.main_menu_keyboard(config)

            await message.answer(text=text, reply_markup=keyboard, parse_mode="HTML")

    @dp.message_handler(IsUser(), state='*', content_types=types.ContentType.ANY)
    async def messages(message: types.Message, state: FSMContext):
        language_code = await db.get_language(message.from_user.id)
        if language_code is None:
            language_code = 'ua'
        config = Config(message.from_user.id, f"languages/{language_code}.ini")
        state = dp.current_state(chat=message.chat.id, user=message.from_user.id)
        current_state = await state.get_state()
        name, lastname = message.from_user.first_name, message.from_user.last_name
        if current_state == "SendScreenshot:send_screenshot":
            link = await telepraph.photo_handler(message=message)
            data = await state.get_data()
            if link:
                info = {
                    "user_id": message.from_user.id,
                    "name": f'{name if name else ""} {lastname if lastname else ""}',
                    "tag": message.from_user.username,
                    "type": data['type'],
                    "screenshot": link
                }
                if info['type'] != "poetry":
                    await db.add_to_stream(data=info)
                else:
                    await db.add_to_poetry(data=info)
                    keyboard = types.InlineKeyboardMarkup()
                    keyboard.add(types.InlineKeyboardButton(text=await config.get('GO_BACK', 'understood'), callback_data='delete'))
                    text = await config.get("ADMIN_ACTIONS", "user_poetry_announcement")

                    admins = await db.is_admin()
                    for admin in admins:
                        await bot.send_message(chat_id=admin, text=text, reply_markup=keyboard)

                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goback'), callback_data='goback'))

                text = await config.get("KINO", "kino_payment_success")

                await message.answer(text=text, reply_markup=keyboard, parse_mode="HTML")
            else:
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goprev'), callback_data='payment'))
                text = await config.get("KINO", "kino_payment_unsuccess") + '\n\n' + data['text_start']

                await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
                await bot.edit_message_text(message_id=data['message_id'], chat_id=message.chat.id, text=text, reply_markup=keyboard, parse_mode="HTML")

    @dp.callback_query_handler(IsUser(), state='*')
    async def process_callback_prev(callback_query: types.CallbackQuery, state: FSMContext):
        language_code = await db.get_language(callback_query.from_user.id)
        user_id = callback_query.from_user.id

        if language_code is None:
            language_code = 'ua'
        config = Config(user_id, f"languages/{language_code}.ini")

        if callback_query.data == 'menu_poetry':
            keyboard = types.InlineKeyboardMarkup(row_width=2)

            keyboard.add(
                types.InlineKeyboardButton(text=await config.get('POETRY', 'instruction'), callback_data='instruction'),
                types.InlineKeyboardButton(text=await config.get('POETRY', 'to_buy'), callback_data='to_buy'))
            keyboard.add(types.InlineKeyboardButton(text=await config.get('GO_BACK', 'goback'), callback_data='goback'))

            text = await config.get('POETRY', 'poetry_text')

            await callback_query.message.edit_text(text=text, reply_markup=keyboard, parse_mode='HTML')

        elif callback_query.data == 'instruction':
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get("GO_BACK", "goprev"), callback_data='menu_poetry'))

            text = await config.get('POETRY', 'instruction_text')

            await callback_query.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")

        elif callback_query.data == 'to_buy':
            keyboard = await inline_keyboards.to_buy_keyboard(config, poetry=True)
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get("GO_BACK", "goprev"), callback_data='menu_poetry'))

            text = await config.get('POETRY', 'to_buy_text')

            await callback_query.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")

        elif callback_query.data.startswith('price_'):
            keyboard = types.InlineKeyboardMarkup()
            if callback_query.data.startswith("price_reg"):
                async with state.proxy() as data:
                    data['type'] = "poetry"
                await SendScreenshot.send_screenshot.set()
                text_parts = {
                    'uah': await config.get("USER", "price_text_2_uah"),
                    'eur': await config.get("USER", "price_text_2_eur"),
                }
                callback, price = callback_query.data.split('/')
                text = f'{await config.get("USER", "price_text_1")}{price}{text_parts[callback.split("_")[-1]]}{await config.get("USER", "price_text_3")}'
                keyboard.add(
                    types.InlineKeyboardButton(text=await config.get("GO_BACK", "goprev"), callback_data='to_buy'))

            elif callback_query.data.startswith("price_kino"):
                text_parts = {
                    'uah': await config.get("USER", "price_text_2_uah"),
                    'eur': await config.get("USER", "price_text_2_eur"),
                }
                callback, price = callback_query.data.split('/')
                text = f'{await config.get("USER", "price_text_1")}{price}{text_parts[callback.split("_")[-1]]}'

                async with state.proxy() as data:
                    data['type'] = (callback_query.data.split("/")[0]).split("_")[2]
                    data['message_id'] = callback_query.message.message_id
                    data['text_start'] = text
                await SendScreenshot.send_screenshot.set()

                text += f'{await config.get("USER", "price_text_3_kino")}'
                keyboard.add(
                    types.InlineKeyboardButton(text=await config.get("GO_BACK", "goprev"), callback_data='payment'))

            try:
                await callback_query.message.edit_text(text=text, reply_markup=keyboard, parse_mode='HTML')
            except BadRequest:
                await bot.delete_message(chat_id=callback_query.message.chat.id,
                                         message_id=callback_query.message.message_id)
                await callback_query.message.answer(text=text, reply_markup=keyboard, parse_mode='HTML')

        elif callback_query.data == 'menu_kinoterapy':
            status = await db.get_is_active()
            if status == 1:
                keyboard = types.InlineKeyboardMarkup(row_width=2)
                keyboard.add(types.InlineKeyboardButton(text=await config.get("KINO", "kino_button_programm"),
                                                        callback_data="programm"),
                             types.InlineKeyboardButton(text=await config.get("KINO", "kino_button_payment"),
                                                        callback_data="payment"))
                keyboard.add(
                    types.InlineKeyboardButton(text=await config.get("GO_BACK", "goback"), callback_data='goback'))

                text = await config.get("KINO", "kino_start")

                try:
                    await callback_query.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
                except BadRequest:
                    await bot.delete_message(chat_id=callback_query.message.chat.id,
                                             message_id=callback_query.message.message_id)
                    await callback_query.message.answer(text=text, reply_markup=keyboard, parse_mode="HTML")

            elif status == 0:
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(
                    types.InlineKeyboardButton(text=await config.get("GO_BACK", "goback"), callback_data='goback'))

                text = await config.get("KINO", "kino_inactive")

                await callback_query.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")

        elif callback_query.data == "programm":
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(text=await config.get("KINO", "kino_button_payment"),
                                                    callback_data="payment"),
                         types.InlineKeyboardButton(text=await config.get("GO_BACK", "goprev"),
                                                    callback_data='menu_kinoterapy'))

            text = await config.get("KINO", "kino_programm")

            await callback_query.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")

        elif callback_query.data == "payment":
            await state.finish()
            keyboard = await inline_keyboards.to_buy_keyboard(config, kinoterapy=True)
            keyboard.add(
                types.InlineKeyboardButton(text=await config.get("GO_BACK", "goprev"), callback_data='menu_kinoterapy'))

            text = (f"<a href='{await config.get('KINO', 'kino_image')}'> </a>"
                    f"{await config.get('KINO', 'kino_payment')}")

            await callback_query.message.edit_text(text=text, reply_markup=keyboard, parse_mode='HTML')



        elif callback_query.data == 'language_change':
            prefix = 'changelang/'
            text = await config.get("CHANGE_LANG", 'text')
            keyboard = await inline_keyboards.language_keyboard(prefix)

            await callback_query.message.edit_text(text=text, reply_markup=keyboard, parse_mode='HTML')

        elif callback_query.data.startswith('changelang/'):
            language = callback_query.data.split('/')[1]
            await db.update_language(user_id=user_id, new_language=language)
            await config.change_path(f'languages/{language}.ini')

            text = await config.get("USER", "user_start")
            keyboard = await inline_keyboards.main_menu_keyboard(config)

            await callback_query.message.answer(text=text, reply_markup=keyboard, parse_mode="HTML")
            await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)

        elif callback_query.data == 'goback':
            text = await config.get("USER", "user_start")
            keyboard = await inline_keyboards.main_menu_keyboard(config)

            await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode='HTML')
            await state.finish()

        elif callback_query.data == "goback_buy":
            text = await config.get("USER", "user_start")
            keyboard = await inline_keyboards.main_menu_keyboard(config)

            await callback_query.message.answer(text, reply_markup=keyboard, parse_mode='HTML')

        elif callback_query.data == 'delete':
            await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
