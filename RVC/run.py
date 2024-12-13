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
    vidos_queue = Queue()
    burunov_queue = Queue()
    queues = {
        'vidos': vidos_queue,
        'burunov': burunov_queue
    }
    if os.getenv('REDIS_URL') is None:
        raise ValueError("REDIS_URL is not set")
    listener = Listener(os.getenv('REDIS_URL'), os.getenv('request_channel'), queues)
    vidos_worker = Process(target=VoiceChanger.start_voice_changer, 
                           args=('vidos', os.getenv('REDIS_URL'), os.getenv('response_channel'), vidos_queue,))
    burunov_worker = Process(target=VoiceChanger.start_voice_changer, 
                             args=('burunov', os.getenv('REDIS_URL'), os.getenv('response_channel'), burunov_queue,))
    
    vidos_worker.start()
    atexit.register(exit_handler, vidos_worker)
    
    burunov_worker.start()
    atexit.register(exit_handler, burunov_worker)
    
    listener.start_listening()