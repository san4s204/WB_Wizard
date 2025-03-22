from aiogram.fsm.state import StatesGroup, State

class TokenState(StatesGroup):
    waiting_for_token = State()
