import logging
import time
import redis
import threading

class Generator:
    @property
    def generation_config(self):
        return self.__generation_config
    
    @property
    def redis(self):
        return self.__redis
    
    def __init__(self, redis_storage, generation_config : dict, 
                 table: int, queue_name: str, max_threads: int):
        self.__redis = redis.from_url(redis_storage, db=table)
        self.__queue_name = queue_name
        self.__generation_config = generation_config
        self.__max_threads = max_threads
        self.__threads : list[threading.Thread] = []
        self.__lock = threading.Lock()
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def start_listening(self):
        self.logger.info("Started listening to the queue: %s", self.__queue_name)
        while True:
            message = self.__redis.lpop(self.__queue_name)
            if message is not None:
                self.logger.info("Received message from queue: %s", message)
                self.__start_generating_thread(message)
            else:
                self.logger.debug("No message in the queue, sleeping for a while.")
            time.sleep(1)
            
    def __start_generating_thread(self, message):
        with self.__lock:
            if len(self.__threads) < self.__max_threads:
                thread = threading.Thread(target=self._start_generating, args=(message,))
                thread.start()
                self.__threads.append(thread)
                self.logger.info("Started new generating thread: %s", thread.name)
            else:
                self.logger.debug("Max threads limit reached. Cannot start new thread.")
            self.__threads = [t for t in self.__threads if t.is_alive()]
    
    def _start_generating(self, message):
        raise NotImplementedError('Method not implemented')