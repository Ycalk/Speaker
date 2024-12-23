import atexit
from multiprocessing import Queue, Process
import os
from app.listener import Listener
from app.worker import VoiceChanger
import logging
import time
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

def exit_handler(process: Process):
    if process.is_alive():
        process.terminate()
        process.join()

def restart_worker(target, args, name):
    logging.error(f"Process {name} terminated. Restarting...")
    new_process = Process(target=target, args=args, name=name)
    new_process.start()
    return new_process


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
    
    redis_url = os.getenv('REDIS_URL')
    response_channel = os.getenv('response_channel')
    
    workers: dict[str, Process] = {}
    
    for model in queues.keys():
        worker_args = (model, redis_url, response_channel, queues[model])
        worker_name = f"worker-{model}"
        process = Process(target=VoiceChanger.start_voice_changer, args=worker_args, name=worker_name)
        process.start()
        workers[worker_name] = process
        atexit.register(exit_handler, process)
    
    listener_args = (os.getenv('REDIS_URL'), os.getenv('request_channel'), queues)
    listener = Process(target=Listener.start_listening, args=listener_args, name="listener")
    listener.start()
    workers["listener"] = listener
    atexit.register(exit_handler, listener)
    
    try:
        while True:
            for name, process in list(workers.items()):
                if not process.is_alive():
                    if name.startswith("worker-"):
                        model = name.split("-")[1]
                        worker_args = (model, redis_url, response_channel, queues[model])
                        workers[name] = restart_worker(VoiceChanger.start_voice_changer, worker_args, name)
                    elif name == "listener":
                        workers[name] = restart_worker(Listener.start_listening, listener_args, name)

            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down all processes...")
        for process in workers.values():
            process.terminate()
            process.join()