import logging
from utils.queue_listener import QueueListener
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
import json
from utils.connector import Connector, AppType
import os
from dotenv import load_dotenv
load_dotenv()

bot_token = os.getenv('TOKEN')
with open('utils/stickers.json', 'r', encoding='utf-8') as f:
    stickers = json.load(f)

texts = json.load(open('utils/texts.json', 'r', encoding='utf-8'))
connector = Connector(AppType.TELEGRAM, os.getenv('SERVER_URL'), os.getenv('SERVER_PORT'), os.getenv('REDIS_STORAGE'))
constants = connector.get_config()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=os.getenv('TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=RedisStorage.from_url(f"{os.getenv('REDIS_STORAGE')}{constants['redis']['fsm_storage_table']}"), bot=bot)
queue_listener = QueueListener(os.getenv('REDIS_STORAGE'), bot, 
                               constants['redis']['generating_queue_table_keys']['voice'], 
                               constants['redis']['generating_queue_table'])