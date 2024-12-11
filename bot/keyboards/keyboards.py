from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import texts, connector

buttons_texts = texts['buttons']

def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=buttons_texts['create'])],
    ], resize_keyboard=True, one_time_keyboard=True)

async def celebrities_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=celebrity['name'], callback_data=celebrity['code'])] 
                  for celebrity in await connector.get_celebrities()])

def behavior_keyboard() -> ReplyKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Хорошо', callback_data='good'), 
             InlineKeyboardButton(text='Плохо', callback_data='bad')],
        ],
    )