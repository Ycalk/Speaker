from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from bot import texts
from keyboards.keyboards import main_keyboard
from handlers.generate import GenerateState
start_router = Router()

@start_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    if not (await state.get_state() == GenerateState.generating):
        await state.clear()
    await message.answer(texts['messages']['welcome'], reply_markup=main_keyboard())


# Debug command
@start_router.message(Command('clear'))
async def cmd_clear(message: Message, state: FSMContext):
    await state.clear()
    await message.answer('State cleared')