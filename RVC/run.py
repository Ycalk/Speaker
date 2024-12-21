import atexit
from multiprocessing import Queue, Process
import os
from app.listener import Listener
from app.worker import VoiceChanger
import logging
from dotenv import load_dotenv
load_dotenv()
logging.basicConfig(level=logging.INFO)

def exit_handler(process):
    if process.is_alive():
        process.terminate()
        process.join()

if __name__ == '__main__':
    
    queues = {
        'vidos': Queue(),
        'burunov': Queue(),
        'musagaliev': Queue(),
        'carnaval': Queue(),
        'lebedev': Queue(),
        'shcherbakova': Queue(),
        'dorohov': Queue(),
        'cross': Queue(),
        'chebatkov': Queue()
    }
    
    if os.getenv('REDIS_URL') is None:
        raise ValueError("REDIS_URL is not set")
    
    listener = Listener(os.getenv('REDIS_URL'), os.getenv('request_channel'), queues)
    
    redis_url = os.getenv('REDIS_URL')
    response_channel = os.getenv('response_channel')
    
    for model in queues.keys():
        worker = Process(target=VoiceChanger.start_voice_changer, 
                         args=(model, redis_url, response_channel, queues[model],))
        worker.start()
        atexit.register(exit_handler, worker)
    
    listener.start_listening()