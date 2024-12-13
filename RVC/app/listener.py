import logging
from redis import Redis
from multiprocessing import Queue
import json

class Listener:
    
    def __init__(self, redis_url, channel, queues: dict[str, Queue]):
        self.redis = Redis.from_url(redis_url)
        self.channel = channel
        self.queues = queues
        self.logger = logging.getLogger(__name__)
        
    def start_listening(self):
        pubsub = self.redis.pubsub()
        pubsub.subscribe(self.channel)
        self.logger.info(f"Listening to {self.channel}")
        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    model = data['model']
                    self.queues[model].put((data['request_id'], data['audio']))
                except Exception as e:
                    self.logger.error(f"Error processing message. Model {message['model']}")
                    self.logger.error(f"Error: {e}")