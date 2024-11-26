from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from bot import texts
from keyboards.keyboards import main_keyboard

start_router = Router()

@start_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(texts['messages']['welcome'], reply_markup=main_keyboard(message.from_user.id))