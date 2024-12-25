import enum
import json
import logging
import datetime
import os
import time
import requests
from handlers.video_generation.everypixel_lipsync_generator import EverypixelLipsyncGenerator
from handlers.generator import Generator
from handlers.generator import Update, Error

class RequestGenerator:
    """Class to generate requests for lip sync API."""
    DEFAULT_REQUEST = {
        "model": "lipsync-1.8.0",
        "input": [
            {"type": "video", "url": ""},
            {"type": "audio", "url": ""}
        ],
        "options": {"output_format": "mp4"},
    }

    @staticmethod
    def generate(video_url: str, audio_url: str) -> dict:
        """Generates a request for the lip sync API."""
        request = RequestGenerator.DEFAULT_REQUEST.copy()
        request['input'][0]['url'] = video_url
        request['input'][1]['url'] = audio_url
        return request

class VideoGenerationStatus(enum.Enum):
    CREATED = 0
    LIP_SYNC_GENERATED = 1
    FRAME_INTERPOLATION_CREATED = 2
    COMPLETED = 3
    FAILED = 4

class VideoGeneration:
    def __init__(self, generator: Generator, request: dict):
        self.status = VideoGenerationStatus.CREATED
        self.request = request
        self.redis = generator.redis
        self.return_video_channel = generator.generation_config['return_video_channel']
        self.processor_request_channel = generator.generation_config['video_processor_request_channel']
        self.processor_response_channel = generator.generation_config['video_processor_response_channel']
        self.g = generator
        self.everypixel_lipsync: EverypixelLipsyncGenerator = generator.generation_config['everypixel_lipsync_generator']
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def _get_storage_url(self, bucket_env: str, path: str) -> str:
        base_url = os.getenv('DATA_STORAGE')
        bucket = os.getenv(bucket_env)
        return f"{base_url}/{bucket}/{path}"

    def get_video_url(self) -> str:
        """Returns the video URL for lip sync."""
        path = self.request['celebrity_code'].replace('_', '/') + "/part1.mp4"
        return self._get_storage_url('VIDEO_DATA_BUCKET', path)

    def get_audio_url(self) -> str:
        """Returns the audio URL for lip sync."""
        celeb_folder = self.request['celebrity_code'].split('_')[0]
        path = f"voice/{celeb_folder}/{self.request['user_name']}.wav"
        return self._get_storage_url('GENERATED_BUCKET', path)

    def create_lip_sync_using_sync_so(self) -> str:
        """Creates a lip sync video and returns its url."""
        self.logger.info("Creating lip sync for request using sync so: %s", self.request)

        try:
            request = RequestGenerator.generate(self.get_video_url(), self.get_audio_url())
            headers = {
                "x-api-key": os.getenv('SYNC_SO_API_KEY'),
                "Content-Type": "application/json"
            }
            api_url = os.getenv('SYNC_SO_API_URL')
            self.logger.info("Sending request to lip sync API: %s", request)
            # Send initial POST request
            response = requests.post(api_url, json=request, headers=headers).json()
            request_id = response['id']

            # Poll for completion
            while True:
                response_status = requests.get(f"{api_url}/{request_id}", headers=headers).json()
                if response_status['status'] == 'COMPLETED':
                    break
                self.logger.debug("Waiting for lip sync generation: %s", response_status)
                time.sleep(3)

            video_url = response_status['outputUrl']

            self.logger.info('Lip sync created %s', video_url)
            return video_url

        except Exception as e:
            self.logger.error("Error during lip sync creation: %s.\nRequest was: %s", 
                              e, self.request)
            self.g.send_notification(Error.LIP_SYNC_FAILED,
                                     self.request['user_id'], self.request['app_type'])
            return None

    def create_lip_sync_using_everypixel(self) -> str:
        self.logger.info("Creating lip sync for request using everypixel: %s", self.request)
        try:
            self.everypixel_lipsync.create_request(self.request['id'], self.get_audio_url(), self.get_video_url())

            # Poll for completion
            attempts = 0
            while True:
                video = self.everypixel_lipsync.get_video(self.request['id'])
                if video:
                    self.logger.info('Lip sync created %s', video)
                    return video
                attempts += 1
                if attempts == 40:
                    self.g.send_notification(Error.LIP_SYNC_FAILED,
                                     self.request['user_id'], self.request['app_type'])
                    self.logger.error("Error: cannot create lipsync using everypixel")
                    return None
                time.sleep(3)

        except Exception as e:
            self.logger.error("Error during lip sync creation: %s.\nRequest was: %s", 
                              e, self.request)
            self.g.send_notification(Error.LIP_SYNC_FAILED,
                                     self.request['user_id'], self.request['app_type'])
            return None

    def start(self):
        """Starts the video generation process."""
        self.request['video_generation_start'] = datetime.datetime.now().isoformat()
        self.logger.info("Starting video generation for request: %s", self.request)
        if self.request['celebrity_code'] in ('chebatkov', 'carnaval', 'shcherbakova', 'cross', 
                                              'vidos_good_v1', 'vidos_good_v2', 'vidos_bad_v3', 'musagaliev'):
            lip_sync_url = self.create_lip_sync_using_everypixel()
        else:
            lip_sync_url = self.create_lip_sync_using_sync_so()
        if lip_sync_url:
            self.g.send_notification(Update.LIP_SYNC_GENERATED,
                                     self.request['user_id'], self.request['app_type'])
            self.status = VideoGenerationStatus.LIP_SYNC_GENERATED
            self.logger.info("Lip sync created for request: %s", self.request)

            try:
                processor_request = {
                    "lip_sync_url": lip_sync_url,
                    "celebrity_code": self.request['celebrity_code'],
                    "user_name": self.request['user_name'],
                    "id": self.request['id']
                }
                self.logger.info("Sending request to video processor: %s", processor_request)
                self.redis.publish(self.processor_request_channel, json.dumps(processor_request))
                self.logger.info("Published request to video processor: %s", processor_request)
                pubsub = self.redis.pubsub()
                pubsub.subscribe(self.processor_response_channel)
                self.logger.info("Subscribed to video processor response channel: %s", self.processor_response_channel)
                
                timeout = 120
                start_time = time.time()
                response = None
                while time.time() - start_time < timeout:
                    message = pubsub.get_message(timeout=1.0)
                    if message and message['type'] == 'message':
                        response = json.loads(message['data'])
                        if response['id'] == self.request['id']:
                            break
                        else:
                            response = None
                            
                final_video_path = response['video_url']
                self.request['video_generation_end'] = datetime.datetime.now().isoformat()
                self.status = VideoGenerationStatus.COMPLETED
                self.request['video'] = final_video_path

                self.redis.publish(self.return_video_channel, json.dumps(self.request))
                self.logger.info("Video generation completed and published.")
                self.g.send_notification(Update.VIDEO_CONCATENATED,
                                         self.request['user_id'], self.request['app_type'])
            except Exception as e:
                self.logger.error("Error during video concatenation: %s", e)
                self.g.send_notification(Error.VIDEO_CONCATENATION_FAILED,
                                         self.request['user_id'], self.request['app_type'])
