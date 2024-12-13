import atexit
from multiprocessing import Process, Queue
import os
from dotenv import load_dotenv

from app import RequestsListener
from video_processor import Worker

def exit_handler(process):
    if process.is_alive():
        process.terminate()
        process.join()

def start_worker(queue: Queue):
    Worker.start_listening(queue, os.getenv('output_redis_channel'), os.getenv('REDIS_STORAGE'))

if __name__ == "__main__":
    load_dotenv()
    queues = [Queue() for _ in range(int(os.getenv('NUM_WORKERS')))]
    
    requests_listener = RequestsListener(os.getenv('input_redis_channel'), os.getenv('REDIS_STORAGE'), queues)
    workers = []
    for queue in queues:
        process = Process(target=start_worker, args=(queue,))
        atexit.register(exit_handler, process)
        workers.append(process)
    
    for i in workers:
        i.start()
    
    requests_listener.start_listening()
        