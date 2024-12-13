import json
import redis as r
from multiprocessing import Queue

class RequestsListener:
    def __init__ (self, input_channel: str, redis_storage_url: str,
                  queues: list[Queue]):
        self.input_channel = input_channel
        self.redis = r.Redis.from_url(redis_storage_url)
        self.queues = queues
        self.__counter = 0
    
    def start_listening(self):
        pubsub = self.redis.pubsub()
        pubsub.subscribe(self.input_channel)
        
        for message in pubsub.listen():
            if message['type'] == 'message':
                queue = self.queues[self.__counter % len(self.queues)]
                self.__counter += 1
                queue.put(message['data'])