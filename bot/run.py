import asyncio

from bot import bot, dp, constants
from handlers.start import start_router
from handlers.generate import generate_router
from utils.connector import AppType
from decouple import config

from utils.listener import ListenerImpl

async def main():
    dp.include_router(start_router)
    dp.include_router(generate_router)
    listener = ListenerImpl(AppType.TELEGRAM, config('REDIS_STORAGE'), 
                            constants['redis']['generating_queue_table'],
                            constants['redis']['fsm_storage_table'],
                            bot)
    await bot.delete_webhook(drop_pending_updates=True)
    await asyncio.gather(
        dp.start_polling(bot),
        listener.listen()
    )
    

if __name__ == "__main__":
    asyncio.run(main())