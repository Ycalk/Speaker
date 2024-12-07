import atexit
import json
import multiprocessing
from handlers.voice_generation.voice_generator import VoiceGenerator
from listeners.listener import start_listeners
from app import main as start_app
from decouple import config

def start_voice_generator(redis_storage, table, queue_name, tts_model_url, api_key, folder_id, 
                          return_voice_channel, voice_changer_request_channel, voice_changer_response_channel):
    voice_generator = VoiceGenerator(
        redis_storage=redis_storage,
        table=table,
        queue_name=queue_name,
        tts_model_url=tts_model_url,
        api_key=api_key,
        folder_id=folder_id,
        return_voice_channel=return_voice_channel,
        voice_changer_request_channel=voice_changer_request_channel,
        voice_changer_response_channel=voice_changer_response_channel
    )
    voice_generator.start_listening()



def exit_handler(process):
    if process.is_alive():
        process.terminate()
        process.join()
        

    
if __name__ == '__main__':
    with open('utils/config.json', 'r') as config_file:
        json_file = json.load(config_file)
        
        listeners = multiprocessing.Process(target=start_listeners, args=(config('REDIS_STORAGE'), json_file,))
        atexit.register(exit_handler, listeners)
        
        redis_storage = config('REDIS_STORAGE')
        table = int(json_file['redis']['generating_queue_table'])
        queue_name = json_file['redis']['generating_queue_table_keys']['voice']
        tts_model_url = json_file['yc']['tts_url']
        api_key = config('YC_API_KEY')
        folder_id = config('YC_FOLDER_ID')
        return_voice_channel = json_file['redis']['channels']['voice_generated']
        voice_changer_request_channel = config('VOICE_CHANGER_REQUEST_CHANNEL')
        voice_changer_response_channel = config('VOICE_CHANGER_RESPONSE_CHANNEL')
        
        voice_generator_process = multiprocessing.Process(
            target=start_voice_generator,
            args=(redis_storage, table, queue_name, tts_model_url, api_key, folder_id, 
                  return_voice_channel, voice_changer_request_channel, voice_changer_response_channel)
        )
        atexit.register(exit_handler, voice_generator_process)
        
                                         
    app = multiprocessing.Process(target=start_app)
    atexit.register(exit_handler, app)
    
    listeners.start()
    app.start()
    voice_generator_process.start()
    listeners.join()
    app.join()
    voice_generator_process.join()