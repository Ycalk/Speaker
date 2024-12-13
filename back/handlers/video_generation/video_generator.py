import logging
import os
import threading
from handlers.generator import Generator
import json

from handlers.video_generation.video_generation import VideoGeneration, VideoGenerationStatus


class VideoGenerator(Generator):
    __max_threads = 10
    
    def __init__(self, redis_storage, table: int, queue_name: str, return_video_channel: str,
                 notification_channel: str):
        logging.basicConfig(level=logging.INFO)
            
        self.generation_requests : list[VideoGeneration] = []
        self.__lock = threading.Lock()
        os.makedirs(os.getenv('video_data_temp'), exist_ok=True)
        super().__init__(redis_storage, {"return_video_channel" : return_video_channel,
                                         "video_processor_request_channel" : os.getenv('video_processor_request_channel'),
                                         "video_processor_response_channel" : os.getenv('video_processor_response_channel')}, 
                         table, queue_name, VideoGenerator.__max_threads, notification_channel)
        
        self.logger = logging.getLogger(__name__)
    
    def _start_generating(self, message):
        self.logger.info("Starting voice generation for message: %s", message)
        try:
            new_generation = VideoGeneration(self, json.loads(message))
            with self.__lock:
                self.generation_requests = [g for g in self.generation_requests 
                                            if g.status not in (VideoGenerationStatus.COMPLETED, VideoGenerationStatus.FAILED)]
                self.generation_requests.append(new_generation)
                new_generation.start()
        except json.JSONDecodeError as e:
            self.logger.error("Failed to decode JSON message: %s", e)
        except Exception as e:
            self.logger.error("An error occurred while video generating: %s", e)