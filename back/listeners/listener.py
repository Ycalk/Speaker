import asyncio

from listeners.impl.generating_request import GeneratingRequestListener
from listeners.impl.voice_generated import VoiceGeneratedListener

async def _start(redis_storage, config):
    gen_request_listener = GeneratingRequestListener(redis_storage, int(config['redis']['generating_queue_table']),
                                         config['redis']['channels']['to_generate'],
                                         config['redis']['generating_queue_table_keys']['voice'])
    voice_generated_listener = VoiceGeneratedListener(redis_storage, int(config['redis']['generating_queue_table']),
                                         config['redis']['channels']['voice_generated'],
                                         config['redis']['generating_queue_table_keys']['video'])
    await asyncio.gather(
        gen_request_listener.listen(),
        voice_generated_listener.listen()
    )

def start_listeners(redis_storage, config):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_start(redis_storage, config))
    loop.run_forever()