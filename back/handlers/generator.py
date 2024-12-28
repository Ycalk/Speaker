import json
import logging
import time
import redis
from concurrent.futures import ThreadPoolExecutor
import enum

class Notification(enum.Enum):
    pass
    
class Update(Notification):
    GENERATION_STARTED = 0
    TTS_GENERATED = 1
    VOICE_GENERATED = 2
    LIP_SYNC_GENERATED = 3
    VIDEO_CONCATENATED = 4

class Error(Notification):
    CANNOT_START = 0
    TTS_FAILED = 1
    VOICE_FAILED = 2
    LIP_SYNC_FAILED = 3
    VIDEO_CONCATENATION_FAILED = 4

class Generator:
    @property
    def generation_config(self):
        return self.__generation_config
    
    @property
    def redis(self):
        return self.__redis
    
    def __init__(self, redis_storage, generation_config : dict, 
                 table: int, queue_name: str, max_threads: int, notification_channel : str):
        self.__redis = redis.from_url(redis_storage, db=table)
        self.__queue_name = queue_name
        self.__generation_config = generation_config
        self.__max_threads = max_threads
        self.__threads = ThreadPoolExecutor(max_workers=max_threads)
        self.__notification_channel = notification_channel
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def send_notification(self, notification: Notification, user_id, app_type):
        message = {
            "notification": str(notification),
            "user_id": user_id,
            "app_type": app_type
        }
        self.__redis.publish(self.__notification_channel, json.dumps(message))
    
    def start_listening(self):
        self.logger.info("Started listening to the queue: %s", self.__queue_name)
        while True:
            if len(self.__threads._threads) <= self.__max_threads:
                message = self.__redis.lpop(self.__queue_name)
                if message is not None:
                    self.logger.info("Received message from queue: %s", message)
                    self.__start_generating_thread(message)
                else:
                    self.logger.debug("No message in the queue, sleeping for a while.")
            else:
                self.logger.debug("Max threads limit reached. Waiting for threads to finish.")
            
            time.sleep(1)

    def __start_generating_thread(self, message):
        future = self.__threads.submit(self._start_generating, message)
        self.logger.info("Started new generating thread: %s", future)
    
    def _start_generating(self, message):
        raise NotImplementedError('Method not implemented')