from aiogram import Router, F
from aiogram.types import Message
from bot import texts, queue_listener
from keyboards.keyboards import celebrities_keyboard, behavior_keyboard, subscribe_keyboard
from keyboards.keyboards import CreateCallback
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from bot import connector, constants
from utils.connector import Gender
from utils.bot_utils import BotUtils

class GenerateState(StatesGroup):
    celebrity_name = State()
    user_name = State()
    behavior = State()
    generating = State()
    
generate_router = Router()
bot_utils = BotUtils()

@generate_router.callback_query(CreateCallback.filter(F.message=='create'))
async def create(query: CallbackQuery, state: FSMContext):
    if (await state.get_state() == GenerateState.generating):
        await query.message.edit_text(
            text=texts['messages']['already_generating'],
            reply_markup=None)
        return
    
    if ((await connector.redis.get_count_of_generations(query.message.chat.id)) != 0 and 
        (not (await bot_utils.check_user_subscription(query.message.chat.id)))):
        await query.message.edit_text(
            text=texts['messages']['channel_subscribe'],
            reply_markup=subscribe_keyboard(bot_utils.channel_url))
        return
    
    try:
        celebrities = await connector.get_celebrities()
            
        await query.message.edit_text(
            text=texts['messages']['choose_celebrity'], 
            reply_markup=celebrities_keyboard(celebrities))
        await state.set_state(GenerateState.celebrity_name)
    except Exception as e:
        await query.message.edit_text(
            text=texts['messages']['maintenance'])

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
    user_data = await state.get_data()
    
    valid_name, gender = await connector.validate_name(message.text, message.from_user.id)
    await state.update_data(gender=str(gender))
    if not valid_name:
        await message.answer(texts['messages']['incorrect_name'].format(symbols_count=constants['MAX_NAME_LENGTH']))
        return
    await state.update_data(name=message.text)
    
    if user_data['celebrity']['code'] != 'vidos':
        await message.answer(texts['messages']['generating'].format(user_name=message.text, 
                                                                celebrity_name=user_data['celebrity']['name']))
        await state.set_state(GenerateState.generating)
        queue_length = await connector.get_queue_length()
        queue_message = await message.answer(texts['messages']['queue_length'].format(queue_length=queue_length))
        queue_listener.add_listening_user(message.chat.id, queue_message.message_id)
        await connector.redis.create_generation_request(
            message.from_user.id, 
            user_data['celebrity']['code'], 
            message.text, str(gender))
    else:
        ending = ""
        if gender == Gender.FEMALE:
            ending = "а"
        elif gender == Gender.UNKNOWN:
            ending = "(а)"
        await message.answer(texts['messages']['behavior'].format(ending=ending, name=message.text.capitalize()), reply_markup=behavior_keyboard())
        await state.set_state(GenerateState.behavior)


@generate_router.callback_query(GenerateState.behavior)
async def behavior(query: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    generating_text = texts['messages']['generating'].format(user_name=user_data['name'].capitalize(), 
                                    celebrity_name=user_data['celebrity']['name'])
    generating_text += f"\nПоведение: <b>{'Хорошее' if query.data == 'good' else 'Плохое'}</b>"
    await query.message.edit_text(generating_text,
                                  reply_markup=None)
    await state.set_state(GenerateState.generating)
    queue_length = await connector.get_queue_length()
    queue_message = await query.message.answer(texts['messages']['queue_length'].format(queue_length=queue_length))
    queue_listener.add_listening_user(query.message.chat.id, queue_message.message_id)
    await connector.redis.create_generation_request(
        query.message.chat.id, 
        f"{user_data['celebrity']['code']}_{query.data}", 
        user_data['name'], user_data['gender'])
    