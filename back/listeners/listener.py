import asyncio

from listeners.generating_request import GeneratingRequestListener

def start_listeners(redis_storage, config):
    listener = GeneratingRequestListener(redis_storage, int(config['redis']['generating_queue_table']),
                                         config['redis']['channels']['to_generate'],
                                         config['redis']['generating_queue_table_keys']['voice'])
    loop = asyncio.get_event_loop()
    loop.run_until_complete(listener.listen())
    loop.run_forever()