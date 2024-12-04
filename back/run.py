import atexit
import multiprocessing
from listeners.generating_request import Listener
from listeners.generating_request import main as start_listener
from app import main as start_app
from decouple import config

def exit_handler():
    listeners.terminate()
    app.terminate()

if __name__ == '__main__':
    atexit.register(exit_handler)
    listeners = multiprocessing.Process(target=start_listener, args=(config('REDIS_STORAGE'), 1,))
    app = multiprocessing.Process(target=start_app)
    
    listeners.start()
    app.start()
    listeners.join()
    app.join()