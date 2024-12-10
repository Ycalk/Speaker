import enum
import json
import logging
import datetime
import os
import time
import requests

from handlers.generator import Generator
from handlers.video_generation.video_processor import VideoProcessor

class RequestGenerator:
    """Class to generate requests for lip sync API."""
    DEFAULT_REQUEST = {
        "model": "lipsync-1.7.1",
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

    def create_lip_sync(self) -> str:
        """Creates a lip sync video and saves it locally."""
        self.request['lip_sync_generation_start'] = datetime.datetime.now().isoformat()
        self.logger.info("Creating lip sync for request: %s", self.request)

        try:
            request = RequestGenerator.generate(self.get_video_url(), self.get_audio_url())
            headers = {
                "x-api-key": os.getenv('SYNC_SO_API_KEY'),
                "Content-Type": "application/json"
            }
            api_url = os.getenv('SYNC_SO_API_URL')

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

            # Save the video locally
            video_url = response_status['outputUrl']
            save_path = os.path.join(os.getenv('video_data_temp'), f"{self.request['id']}_lp.mp4")
            with open(save_path, "wb") as f:
                video_response = requests.get(video_url)
                f.write(video_response.content)

            self.logger.info('Lip sync created and saved to %s', save_path)
            return save_path

        except Exception as e:
            self.logger.error("Error during lip sync creation: %s.\nResponse was %s", e, response)
            return None

    def start(self):
        """Starts the video generation process."""
        self.request['video_generation_start'] = datetime.datetime.now().isoformat()
        self.logger.info("Starting video generation for request: %s", self.request)

        lip_sync_path = self.create_lip_sync()
        if lip_sync_path:
            self.status = VideoGenerationStatus.LIP_SYNC_GENERATED
            self.logger.info("Lip sync created for request: %s", self.request)

            final_video_path = os.path.join(os.getenv('video_data_temp'), f"{self.request['id']}_final.mp4")
            part2_path = os.path.join("handlers/video_generation/data", 
                                      self.request['celebrity_code'].replace('_', '/'), "part2.mp4")

            processor = VideoProcessor()
            processor.concatenate_videos(lip_sync_path, part2_path, final_video_path)
            os.remove(lip_sync_path)
            self.request['video_generated'] = datetime.datetime.now().isoformat()
            self.status = VideoGenerationStatus.COMPLETED
            self.request['video'] = final_video_path

            self.redis.publish(self.return_video_channel, json.dumps(self.request))
            self.logger.info("Video generation completed and published.")
