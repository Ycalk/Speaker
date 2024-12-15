from aiogram import Router, F
from keyboards.keyboards import SubscribeCallback
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from utils.bot_utils import BotUtils
from bot import texts
from keyboards.keyboards import celebrities_keyboard
from handlers.generate import GenerateState

subscription_router = Router()
bot_utils = BotUtils()


@subscription_router.callback_query(SubscribeCallback.filter(F.action=='subscribed'))
async def subscribed(query: CallbackQuery, state: FSMContext):
    if not (await bot_utils.check_user_subscription(query.message.chat.id)):
        await query.answer("Ты еще не подписался")
    else:
        await query.message.edit_text(
            text=texts['messages']['choose_celebrity'], 
            reply_markup=await celebrities_keyboard())
        await state.set_state(GenerateState.celebrity_name)