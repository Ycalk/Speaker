import logging
import os
from handlers.video_generation.everypixel_lipsync_generator import EverypixelLipsyncGenerator
from handlers.generator import Generator
import json
from handlers.video_generation.video_generation import VideoGeneration, VideoGenerationStatus
from handlers.generator import Error
from dotenv import load_dotenv
load_dotenv()


class VideoGenerator(Generator):
    __max_threads = os.getenv('VIDEO_GENERATOR_WORKERS')
    
    def __init__(self, redis_storage, table: int, queue_name: str, return_video_channel: str,
                 notification_channel: str):
        logging.basicConfig(level=logging.INFO)
        everypixel_accounts_info = os.getenv('EVERYPIXEL_ACCS_INFO').split('<>')
        everypixel_celebs = os.getenv('EVERYPIXEL_CELEBS')
        if everypixel_celebs:
            everypixel_celebs = everypixel_celebs.split(',')
        else:
            everypixel_celebs = []
        everypixel_accounts = [acc.split("::") for acc in everypixel_accounts_info]
        os.makedirs(os.getenv('video_data_temp'), exist_ok=True)
        super().__init__(redis_storage, {"return_video_channel" : return_video_channel,
                                         "video_processor_request_channel" : os.getenv('video_processor_request_channel'),
                                         "video_processor_response_channel" : os.getenv('video_processor_response_channel'),
                                         "everypixel_lipsync_generator": EverypixelLipsyncGenerator(everypixel_accounts),
                                         "everypixel_celebs": everypixel_celebs,}, 
                         table, queue_name, VideoGenerator.__max_threads, notification_channel)
        
        self.logger = logging.getLogger(__name__)
    
    def _start_generating(self, message):
        self.logger.info("Starting video generation for message: %s", message)
        try:
            new_generation = VideoGeneration(self, json.loads(message))
            new_generation.start()
        except json.JSONDecodeError as e:
            self.logger.error("Failed to decode JSON message: %s", e)
        except Exception as e:
            self.logger.error("An error occurred while video generating: %s", e)
            data = json.loads(message)
            super().send_notification(Error.CANNOT_START, data['user_id'], data['app_type'])