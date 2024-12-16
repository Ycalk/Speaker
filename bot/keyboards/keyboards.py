from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData
from bot import texts

class CreateCallback(CallbackData, prefix="create"):
    message: str

class SubscribeCallback(CallbackData, prefix="subscribe"):
    action: str

buttons_texts = texts['buttons']

def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons_texts['create'], 
                              callback_data=CreateCallback(message='create').pack())],
    ],)

def celebrities_keyboard(celebrities) -> InlineKeyboardMarkup:
    
    buttons = [InlineKeyboardButton(text=celebrity['name'], callback_data=celebrity['code']) for celebrity in celebrities]
    
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    
    return InlineKeyboardMarkup(inline_keyboard=rows)

def behavior_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text='Хорошо', callback_data='good'),
                          InlineKeyboardButton(text='Плохо', callback_data='bad')]]
    )

def subscribe_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text='Подписаться', url=url)],
            [InlineKeyboardButton(text='Я уже подписан(а)', callback_data=SubscribeCallback(action='subscribed').pack())]
        ],
    )