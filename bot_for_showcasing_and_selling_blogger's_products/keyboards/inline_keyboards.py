# File for generating keyboards based on specific needs. Mainly used for generating menus consisting of inline buttons 
# (for example, a list of users, each represented as a separate button. Pressing a button triggers a separate handler with information about the user).
# Also demonstrates the use of pagination.

from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import files_detect
from database import db


async def create_inline_keyboard(items: list, start_callback: str) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = []

    for item in items:
        callback_data = f'{start_callback}/{item}'
        buttons.append(InlineKeyboardButton(text=item, callback_data=callback_data))

    for i in range(0, len(buttons), 2):
        row = buttons[i:i + 2]
        keyboard.add(*row)
    return keyboard


async def main_menu_keyboard(config):
    buttons = [
        await config.get('MAIN_MENU', 'poetry'),
        await config.get('MAIN_MENU', 'kinoterapy')
    ]
    callback_data = ['menu_poetry', 'menu_kinoterapy']
    result = []
    keyboard = InlineKeyboardMarkup(row_width=2)
    for text, data in zip(buttons, callback_data):
        result.append(InlineKeyboardButton(text=text, callback_data=data))
    for i in range(0, len(result), 2):
        row = result[i:i + 2]
        keyboard.add(*row)
    return keyboard


async def admin_menu_keyboard(config, message_id=None):
    buttons = [
        await config.get('ADMIN_MENU', 'invoices'),
        await config.get('ADMIN_MENU', 'all_payed'),
        await config.get('ADMIN_MENU', 'call_back'),
        await config.get('ADMIN_MENU', 'push'),
        await config.get('ADMIN_MENU', 'poetry')
    ]
    callback_data = ['menu_invoices', 'menu_all_payed', "call_back", 'menu_push', 'menu_poetry']
    result = []
    keyboard = InlineKeyboardMarkup(row_width=2)
    for text, data in zip(buttons, callback_data):
        result.append(InlineKeyboardButton(text=text, callback_data=data))
    for i in range(0, len(result), 2):
        row = result[i:i + 2]
        keyboard.add(*row)

    keyboard.add(InlineKeyboardButton(text=await config.get('ADMIN_MENU', 'settings'), callback_data="menu_settings"))
    return keyboard


async def language_keyboard(prefix):
    languages = await files_detect.list_files_async('languages')
    button_list = await files_detect.prettify_language_codes(languages)
    keyboard = InlineKeyboardMarkup()

    for language, button_text in zip(languages, button_list[0]):
        callback_data = f'{prefix}{language}'
        keyboard.add(types.InlineKeyboardButton(text=button_text, callback_data=callback_data))
    return keyboard


async def to_buy_keyboard(config, poetry=None, kinoterapy=None):
    keyboard = InlineKeyboardMarkup()
    if poetry:
        prices = {
        'price_reg_uah': await db.get_price('regeneration_uah'),
        'price_reg_eur': await db.get_price('regeneration_eur')
        }
    elif kinoterapy:
        prices = {
        'price_kino_simple_uah': await db.get_price('simple_uah'),
        'price_kino_simple_eur': await db.get_price('simple_eur'),
        'price_kino_personal_uah': await db.get_price('personal_uah'),
        'price_kino_personal_eur': await db.get_price('personal_eur')
        }

    for callback, value in prices.items():
        text = f"{await config.get('USER', 'price_button')}{callback.split('_')[-1].upper()}"
        if "personal" in callback.split("_"):
            text += await config.get('USER', 'type_button')
        callback = f"{callback}/{value}"
        keyboard.add(InlineKeyboardButton(text=text, callback_data=callback))

    return keyboard


async def call_back_keyboard(config, page: int = 1, per_page=5):
    users = await db.with_call_back()
    if not users:
        return None

    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    current_page_users = users[start_index:end_index]

    keyboard = InlineKeyboardMarkup()
    for user in current_page_users:
        user_id, name = user
        text = name
        callback = f"cb/{user_id}"

        keyboard.add(InlineKeyboardButton(text=text, callback_data=callback))

    if start_index > 0 and end_index < len(users):
        keyboard.row(
            InlineKeyboardButton(text="⬅", callback_data=f"page_cb/{page - 1}"),
            InlineKeyboardButton(text="➡", callback_data=f"page_cb/{page + 1}"))
    elif start_index > 0:
        keyboard.add(InlineKeyboardButton(text="⬅", callback_data=f"page_cb/{page - 1}"))
    elif end_index < len(users):
        keyboard.add(InlineKeyboardButton(text="➡", callback_data=f"page_cb/{page + 1}"))
    keyboard.add(types.InlineKeyboardButton(text=await config.get("GO_BACK", "goback"), callback_data="goback"))

    return keyboard


async def request_keyboard(config, page: int = 1, per_page=5):
    all_requests = await db.invoices()
    if not all_requests:
        return None
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    current_page_requests = all_requests[start_index:end_index]

    keyboard = InlineKeyboardMarkup()
    info_dict = {
        "personal": await config.get("ADMIN_ACTIONS", "info_dict_personal"),
        "simple": await config.get("ADMIN_ACTIONS", "info_dict_simple")
    }

    for request in current_page_requests:
        text = info_dict[request[2]]
        callback = f"request/{request[0]}"

        keyboard.add(InlineKeyboardButton(text=text, callback_data=callback))

    if start_index > 0 and end_index < len(all_requests):
        keyboard.row(
            InlineKeyboardButton(text="⬅", callback_data=f"page_request/{page - 1}"),
            InlineKeyboardButton(text="➡", callback_data=f"page_request/{page + 1}"))
    elif start_index > 0:
        keyboard.add(InlineKeyboardButton(text="⬅", callback_data=f"page_request/{page - 1}"))
    elif end_index < len(all_requests):
        keyboard.add(InlineKeyboardButton(text="➡", callback_data=f"page_request/{page + 1}"))

    return keyboard


async def poetry_keyboard(config):
    all_requests = await db.poetry_invoices()
    if not all_requests:
        return None
    
    keyboard = InlineKeyboardMarkup()

    for request in all_requests:
        text = request[1]
        callback = f"poetry_request/{request[0]}"

        keyboard.add(InlineKeyboardButton(text=text, callback_data=callback))

    return keyboard


async def accepted_keyboard(config, page: int = 1, per_page=5):
    all_requests = await db.accepted_invoices()
    if not all_requests:
        return None

    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    current_page_requests = all_requests[start_index:end_index]
    
    keyboard = InlineKeyboardMarkup()
    for request in current_page_requests:
        text = f"{request[1]}"
        callback = f"payed/{request[0]}"

        keyboard.add(InlineKeyboardButton(text=text, callback_data=callback))

    if start_index > 0 and end_index < len(all_requests):
        keyboard.row(
            InlineKeyboardButton(text="⬅", callback_data=f"page_payed/{page - 1}"),
            InlineKeyboardButton(text="➡", callback_data=f"page_payed/{page + 1}"))
    elif start_index > 0:
        keyboard.add(InlineKeyboardButton(text="⬅", callback_data=f"page_payed/{page - 1}"))
    elif end_index < len(all_requests):
        keyboard.add(InlineKeyboardButton(text="➡", callback_data=f"page_payed/{page + 1}"))

    return keyboard