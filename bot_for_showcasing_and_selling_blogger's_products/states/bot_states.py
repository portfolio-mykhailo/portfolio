# List of states for Finite State Machine (FSM)

from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.storage import FSMContext


class SetPrice(StatesGroup):
    set_price_uah = State()
    set_price_eur = State()


class PUSH(StatesGroup):
    add_message = State()


class SendScreenshot(StatesGroup):
    send_screenshot = State()


class CreateChannel(StatesGroup):
    channel_name = State()
    channel_description = State()

class CreateGroup(StatesGroup):
    group_name = State()
    group_description = State()