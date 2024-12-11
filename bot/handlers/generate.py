from aiogram import Router, F
from aiogram.types import Message
from bot import texts
from keyboards.keyboards import celebrities_keyboard, behavior_keyboard
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from bot import connector, constants

class GenerateState(StatesGroup):
    celebrity_name = State()
    user_name = State()
    behavior = State()
    generating = State()
    
generate_router = Router()

@generate_router.message(F.text == texts['buttons']['create'])
async def create(message: Message, state: FSMContext):
    if (await state.get_state() == GenerateState.generating):
        await message.answer(texts['messages']['already_generating'])
        return
    await message.answer(texts['messages']['choose_celebrity'], reply_markup=await celebrities_keyboard())
    await state.set_state(GenerateState.celebrity_name)

@generate_router.callback_query(GenerateState.celebrity_name)
async def celebrity_name(query: CallbackQuery, state: FSMContext):
    celebrity = await connector.utils.get_celebrity(query.data)
    await state.update_data(celebrity=celebrity)
    await query.message.edit_text(texts['messages']['enter_name']
                                  .format(celebrity=celebrity['name']),
                                  reply_markup=None)
    await state.set_state(GenerateState.user_name)

@generate_router.message(GenerateState.user_name)
async def user_name(message: Message, state: FSMContext):
    
    def is_correct(name: str) -> bool:
        return name.isalpha() and len(name) <= constants['MAX_NAME_LENGTH']
    
    user_data = await state.get_data()
    
    if not is_correct(message.text):
        await message.answer(texts['messages']['incorrect_name'].format(symbols_count=constants['MAX_NAME_LENGTH']))
        return
    
    if not await connector.validate_name(message.text):
        await message.answer(texts['messages']['invalid_name'])
        return
    await state.update_data(name=message.text)
    
    if user_data['celebrity']['code'] != 'vidos':
        await message.answer(texts['messages']['generating'].format(user_name=message.text, 
                                                                celebrity_name=user_data['celebrity']['name']))
        await state.set_state(GenerateState.generating)
        await connector.redis.create_generation_request(message.from_user.id, user_data['celebrity']['code'], message.text)
    else:
        await message.answer(texts['messages']['behavior'], reply_markup=behavior_keyboard())
        await state.set_state(GenerateState.behavior)


@generate_router.callback_query(GenerateState.behavior)
async def behavior(query: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    await state.update_data(celebrity = {'code': user_data['celebrity']['code'] + f"_{query.data}", 
                                         'name': user_data['celebrity']['name']})

    await query.message.edit_text(texts['messages']['generating']
                                  .format(user_name=user_data['name'], 
                                    celebrity_name=user_data['celebrity']['name']),
                                  reply_markup=None)
    await state.set_state(GenerateState.generating)
    await connector.redis.create_generation_request(
        query.message.chat.id, 
        f"{user_data['celebrity']['code']}_{query.data}", 
        user_data['name'],)
    