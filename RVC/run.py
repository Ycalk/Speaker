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
    musagaliev_queue = Queue()
    carnaval_queue = Queue()
    lebedev_queue = Queue()
    shcherbakova_queue = Queue()
    dorohov_queue = Queue()
    cross_queue = Queue()
    
    queues = {
        'vidos': vidos_queue,
        'burunov': burunov_queue,
        'musagaliev': musagaliev_queue,
        'carnaval': carnaval_queue,
        'lebedev': lebedev_queue,
        'shcherbakova': shcherbakova_queue,
        'dorohov': dorohov_queue,
        'cross': cross_queue
    }
    
    if os.getenv('REDIS_URL') is None:
        raise ValueError("REDIS_URL is not set")
    
    listener = Listener(os.getenv('REDIS_URL'), os.getenv('request_channel'), queues)
    
    vidos_worker = Process(target=VoiceChanger.start_voice_changer, 
                           args=('vidos', os.getenv('REDIS_URL'), os.getenv('response_channel'), vidos_queue,))
    
    burunov_worker = Process(target=VoiceChanger.start_voice_changer, 
                             args=('burunov', os.getenv('REDIS_URL'), os.getenv('response_channel'), burunov_queue,))
    
    musagaliev_worker = Process(target=VoiceChanger.start_voice_changer,
                                args=('musagaliev', os.getenv('REDIS_URL'), os.getenv('response_channel'), musagaliev_queue,))
    
    carnaval_worker = Process(target=VoiceChanger.start_voice_changer,
                                args=('carnaval', os.getenv('REDIS_URL'), os.getenv('response_channel'), carnaval_queue,))
    
    lebedev_worker = Process(target=VoiceChanger.start_voice_changer,
                                args=('lebedev', os.getenv('REDIS_URL'), os.getenv('response_channel'), lebedev_queue,))
    
    shcherbakova_worker = Process(target=VoiceChanger.start_voice_changer,
                                args=('shcherbakova', os.getenv('REDIS_URL'), os.getenv('response_channel'), shcherbakova_queue,))
    
    dorohov_worker = Process(target=VoiceChanger.start_voice_changer,
                                args=('dorohov', os.getenv('REDIS_URL'), os.getenv('response_channel'), dorohov_queue,))
    
    cross_worker = Process(target=VoiceChanger.start_voice_changer,
                                args=('cross', os.getenv('REDIS_URL'), os.getenv('response_channel'), cross_queue,))
    
    vidos_worker.start()
    atexit.register(exit_handler, vidos_worker)
    
    burunov_worker.start()
    atexit.register(exit_handler, burunov_worker)
    
    musagaliev_worker.start()
    atexit.register(exit_handler, musagaliev_worker)
    
    carnaval_worker.start()
    atexit.register(exit_handler, carnaval_worker)
    
    lebedev_worker.start()
    atexit.register(exit_handler, lebedev_worker)
    
    shcherbakova_worker.start()
    atexit.register(exit_handler, shcherbakova_worker)
    
    dorohov_worker.start()
    atexit.register(exit_handler, dorohov_worker)
    
    cross_worker.start()
    atexit.register(exit_handler, cross_worker)
    
    listener.start_listening()