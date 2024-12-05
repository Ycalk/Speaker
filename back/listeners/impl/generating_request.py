import json
from listeners.base import Listener
import logging
import uuid

class GeneratingRequestListener (Listener):
    
    def __init__(self, storage: str, generating_queue_table: int, channel:str, queue_name: str):
        super().__init__(storage, generating_queue_table, channel)
        self.__queue_name = queue_name
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    async def handler(self, data : dict):
        self.logger.info("Received data: %s", data)
        try:
            data['id'] = str(uuid.uuid4())
            await self._redis.rpush(self.__queue_name, json.dumps(data))
            self.logger.info("Processed data and pushed to queue: %s", data)
        except json.JSONDecodeError as e:
            self.logger.error("Failed to decode JSON data: %s", e)
        except Exception as e:
            self.logger.error("An error occurred: %s", e)