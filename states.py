from aiogram.fsm.state import State, StatesGroup

class UserStates(StatesGroup):
    waiting_fullname = State()
    waiting_lastname = State()
    waiting_age = State()
    waiting_phone = State()
    waiting_role = State()
    waiting_anonymous = State()
    waiting_message = State()
    waiting_file = State()
    waiting_confirm = State()
