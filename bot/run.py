import asyncio
import os
from bot import bot, dp, constants
from handlers.start import start_router
from handlers.generate import generate_router
from handlers.subscription import subscription_router
from utils.connector import AppType
from dotenv import load_dotenv
load_dotenv()

from utils.listener import ListenerImpl

async def main():
    dp.include_router(start_router)
    dp.include_router(generate_router)
    dp.include_router(subscription_router)
    listener = ListenerImpl(AppType.TELEGRAM, os.getenv('REDIS_STORAGE'), 
                            constants['redis']['generating_queue_table'],
                            constants['redis']['fsm_storage_table'],
                            bot)
    await bot.delete_webhook(drop_pending_updates=True)
    await asyncio.gather(
        dp.start_polling(bot),
        listener.listen(),
        listener.notifications_listener()
    )
    

if __name__ == "__main__":
    asyncio.run(main())