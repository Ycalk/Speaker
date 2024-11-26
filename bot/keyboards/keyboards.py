from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot import admins, texts, connector

buttons_texts = texts['buttons']

def main_keyboard(telegram_id: int) -> ReplyKeyboardMarkup:
    kb_list = [
        [KeyboardButton(text=buttons_texts['create'])],
    ]
    if telegram_id in admins:
        kb_list.append([KeyboardButton(text=buttons_texts['admin'])])
    return ReplyKeyboardMarkup(keyboard=kb_list, resize_keyboard=True, one_time_keyboard=True)

def celebrities_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=celebrity['name'], callback_data=celebrity['code'])] 
                  for celebrity in connector.get_celebrities()])