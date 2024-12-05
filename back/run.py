import atexit
import json
import multiprocessing
from listeners.listener import start_listeners
from app import main as start_app
from decouple import config

def exit_handler():
    listeners.terminate()
    app.terminate()

if __name__ == '__main__':
    atexit.register(exit_handler)
    with open('utils/config.json', 'r') as config_file:
        listeners = multiprocessing.Process(target=start_listeners, args=(config('REDIS_STORAGE'), json.load(config_file),))
    app = multiprocessing.Process(target=start_app)
    
    listeners.start()
    app.start()
    listeners.join()
    app.join()