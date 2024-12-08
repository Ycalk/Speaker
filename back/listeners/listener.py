import asyncio
import os
from boto3 import Session
from listeners.impl.generating_request import GeneratingRequestListener
from listeners.impl.video_generated import VideoGeneratedListener
from listeners.impl.voice_generated import VoiceGeneratedListener

async def _start(redis_storage, config):
    session = Session(
        aws_access_key_id=os.getenv('YC_STATIC_KEY_ID'),
        aws_secret_access_key=os.getenv('YC_STATIC_KEY'),
        region_name='ru-central1'  
    )
    s3 = session.client(service_name='s3', endpoint_url='https://storage.yandexcloud.net')
    
    gen_request_listener = GeneratingRequestListener(redis_storage, int(config['redis']['generating_queue_table']),
                                         config['redis']['channels']['to_generate'],
                                         config['redis']['generating_queue_table_keys']['voice'], s3, 
                                         config['redis']['channels']['voice_generated'])
    voice_generated_listener = VoiceGeneratedListener(redis_storage, int(config['redis']['generating_queue_table']),
                                         config['redis']['channels']['voice_generated'],
                                         config['redis']['generating_queue_table_keys']['video'], s3)
    
    video_generated_listener = VideoGeneratedListener(redis_storage, int(config['redis']['generating_queue_table']),
                                            config['redis']['channels']['video_generated'], s3,
                                            config['redis']['channels']['generated'])
    
    await asyncio.gather(
        gen_request_listener.listen(),
        voice_generated_listener.listen(),
        video_generated_listener.listen()
    )

def start_listeners(redis_storage, config):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_start(redis_storage, config))
    loop.run_forever()