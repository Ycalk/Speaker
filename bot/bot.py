import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from decouple import config
import json
from utils.connector import Connector

admins = [int(admin_id) for admin_id in config('ADMINS').split(',')]
texts = json.load(open('utils/texts.json', 'r', encoding='utf-8'))
connector = Connector("", "")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=config('TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=RedisStorage.from_url(config('REDIS_FSM_STORAGE')))