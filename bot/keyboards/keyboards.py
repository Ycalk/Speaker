from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from bot import texts, connector

class CreateCallback(CallbackData, prefix="create"):
    message: str

buttons_texts = texts['buttons']

def main_keyboard() -> ReplyKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons_texts['create'], 
                              callback_data=CreateCallback(message='create').pack())],
    ],)

async def celebrities_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=celebrity['name'], callback_data=celebrity['code'])] 
                  for celebrity in await connector.get_celebrities()])

def behavior_keyboard(show_bad : bool) -> ReplyKeyboardMarkup:
    buttons = [InlineKeyboardButton(text='Хорошо', callback_data='good')]
    
    if show_bad:
        buttons.append(InlineKeyboardButton(text='Плохо', callback_data='bad'))
    return InlineKeyboardMarkup(
        inline_keyboard=[buttons]
    )