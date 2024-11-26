from aiogram import Router, F
from aiogram.types import Message
from bot import texts
from keyboards.keyboards import celebrities_keyboard
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from bot import connector
from utils.connector import Connector

class GenerateState(StatesGroup):
    celebrity_name = State()
    user_name = State()
    
generate_router = Router()

@generate_router.message(F.text == texts['buttons']['create'])
async def create(message: Message, state: FSMContext):
    await message.answer(texts['messages']['choose_celebrity'], reply_markup=celebrities_keyboard())
    await state.set_state(GenerateState.celebrity_name)

@generate_router.callback_query(GenerateState.celebrity_name)
async def celebrity_name(query: CallbackQuery, state: FSMContext):
    await query.message.edit_text(texts['messages']['enter_name']
                                  .format(celebrity=Connector.Utils.get_celebrity(connector, query.data)['name']),
                                  reply_markup=None)
    await state.set_state(GenerateState.user_name)