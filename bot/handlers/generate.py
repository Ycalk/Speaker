from aiogram import Router, F
from aiogram.types import Message
from bot import texts, queue_listener, stickers, bot
from keyboards.keyboards import celebrities_keyboard, behavior_keyboard, subscribe_keyboard, check_settings_keyboard
from keyboards.keyboards import CreateCallback, CheckSettingsCallback
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from bot import connector, constants
from utils.connector import Gender
from utils.bot_utils import BotUtils
from aiogram import types
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import BufferedInputFile
import logging

class GenerateState(StatesGroup):
    celebrity_name = State()
    user_name = State()
    behavior = State()
    generating = State()
    
generate_router = Router()
bot_utils = BotUtils()

async def check_user_privacy_settings(user_id: int, is_premium) -> dict:
    if not is_premium:
        return {
            "can_send_video": True,
            "can_send_voice": True
        }
    results = {
        "can_send_video": False,
        "can_send_voice": False
    }
    
    try:
        voice_data = b'test audio data'
        voice_file = BufferedInputFile(
            voice_data,
            filename="test.ogg"
        )
        
        try:
            voice_msg = await bot.send_voice(
                chat_id=user_id,
                voice=voice_file,
                caption="Проверка прав на отправку аудио..."
            )
            await bot.delete_message(chat_id=user_id, message_id=voice_msg.message_id)
            results["can_send_voice"] = True
        except TelegramForbiddenError:
            results["can_send_voice"] = False
        except Exception as e:
            logging.error(f"Ошибка при проверке прав на аудио: {e}")
            
        video_data = b'test video data'
        video_file = BufferedInputFile(
            video_data,
            filename="test.mp4"
        )
        
        try:
            video_msg = await bot.send_video_note(
                chat_id=user_id,
                video_note=video_file
            )
            await bot.delete_message(chat_id=user_id, message_id=video_msg.message_id)
            results["can_send_video"] = True
        except TelegramForbiddenError:
            results["can_send_video"] = False
        except Exception as e:
            logging.error(f"Ошибка при проверке прав на видео: {e}")
            
    except Exception as e:
        logging.error(f"Общая ошибка при проверке прав: {e}")
    
    return results

@generate_router.callback_query(CreateCallback.filter())
async def create(query: CallbackQuery, callback_data: CreateCallback, state: FSMContext):
    if callback_data.message == 'create':
        try:
            permissions = await check_user_privacy_settings(query.from_user.id, query.from_user.is_premium)
            
            if not (permissions["can_send_video"] and permissions["can_send_voice"]):
                await query.message.edit_text(
                    text=texts['messages']['examination'],
                    reply_markup=check_settings_keyboard()
                )
                return
                
            if (await state.get_state() == GenerateState.generating):
                await query.message.edit_text(
                    text=texts['messages']['already_generating'],
                    reply_markup=None)
                return
            
            if ((await connector.redis.get_count_of_generations(query.message.chat.id)) != 0 and 
                (not (await bot_utils.check_user_subscription(query.message.chat.id)))):
                await query.message.edit_reply_markup(reply_markup=None)
                await query.message.answer(
                    text=texts['messages']['channel_subscribe'],
                    reply_markup=subscribe_keyboard(bot_utils.channel_url))
                return
                
            celebrities = await connector.get_celebrities()
            await query.message.edit_reply_markup(reply_markup=None)
            await query.message.answer(
                text=texts['messages']['choose_celebrity'], 
                reply_markup=celebrities_keyboard(celebrities))
            await state.set_state(GenerateState.celebrity_name)
        except Exception as e:
            logging.error(f"Ошибка при создании: {e}")
            await query.message.delete()
            await query.message.answer_sticker(stickers['maintenance'])

@generate_router.callback_query(CheckSettingsCallback.filter())
async def check_settings(query: CallbackQuery, state: FSMContext):
    try:
        permissions = await check_user_privacy_settings(query.from_user.id)
        
        if permissions["can_send_video"] and permissions["can_send_voice"]:
            celebrities = await connector.get_celebrities()
            await query.message.edit_text(
                text=texts['messages']['choose_celebrity'],
                reply_markup=celebrities_keyboard(celebrities)
            )
            await state.set_state(GenerateState.celebrity_name)
        else:
            await query.message.edit_text(
                text=texts['messages']['examination'],
                reply_markup=check_settings_keyboard()
            )
    except Exception as e:
        logging.error(f"Ошибка при проверке настроек: {e}")
        await query.message.edit_text(texts['messages']['generation_error'])

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
        await message.answer_sticker(stickers['generating'])
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
    await query.message.answer_sticker(stickers['generating'])
    await connector.redis.create_generation_request(
        query.message.chat.id, 
        f"{user_data['celebrity']['code']}_{query.data}", 
        user_data['name'], user_data['gender'])
    queue_listener.add_listening_user(query.message.chat.id, queue_message.message_id)
    