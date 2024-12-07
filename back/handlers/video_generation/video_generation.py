import enum
import logging
import datetime
import os
import time

import requests

from handlers.generator import Generator

class _RequestGenerator:
    default_request = {
        "model": "lipsync-1.7.1",
        "input": [
            {
                "type": "video",
                "url": ""
            },
            {
                "type": "audio",
                "url": ""
            }
        ],
        "options": {"output_format": "mp4"},
    }
    
    @staticmethod
    def get_request(video_url: str, audio_url: str) -> dict:
        request = _RequestGenerator.default_request
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
    
    def __init__(self, g : Generator, request: dict):
        self.__status = VideoGenerationStatus.CREATED
        self.request = request
        self.redis = g.redis
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    
    def get_video_url(self):
        storage_url = f"{os.getenv('DATA_STORAGE')}/{os.getenv('VIDEO_DATA_BUCKET')}"
        return f"{storage_url}/{self.request['celebrity_code'].replace('_','/')}/part1.mp4"
    
    def get_audio_url(self):
        storage_url = f"{os.getenv('DATA_STORAGE')}/{os.getenv('GENERATED_BUCKET')}"
        return f"{storage_url}/voice/{self.request['celebrity_code'].split('_')[0]}/{self.request['user_name']}.wav"
    
    def create_lip_sync(self):
        self.request['lip_sync_generation_start'] = datetime.datetime.now().isoformat()
        self.logger.info("Creating lip sync for request: %s", self.request)
        request = _RequestGenerator.get_request(self.get_video_url(), self.get_audio_url())
        headers = {
            "x-api-key": os.getenv('SYNC_SO_API_KEY'),
            "Content-Type": "application/json"
        }
        try:
            api_url = os.getenv('SYNC_SO_API_URL')
            response = requests.request("POST", api_url, json=request, headers=headers)
            self.logger.info("Received response: %s", response.text)
            response = response.json()
            request_id = response['id']
            response_status = requests.request("GET", f"{api_url}/{request_id}", headers=headers)
            while response_status.json()['status'] != 'COMPLETED':
                response_status = requests.request("GET", f"{api_url}/{request_id}", headers=headers)
                self.logger.debug("Received lip sync generating response: %s", response_status.json())
                time.sleep(3)
            video_url = response_status.json()['outputUrl']
            self.logger.info('Lip sync created successfully. Saving ...')
            with open(f"{os.getenv('video_data_temp')}/{self.request['id']}.mp4", "wb") as f:
                response = requests.get(video_url)
                f.write(response.content)     
            return True
        except Exception as e:
            self.logger.error("An error occurred while creating lip sync: %s", e)
            return False
        
    
    @property
    def status(self):
        return self.__status
    
    def start(self):
        self.request['video_generation_start'] = datetime.datetime.now().isoformat()
        self.logger.info("Starting video generation for request: %s", self.request)
        if self.create_lip_sync():
            self.__status = VideoGenerationStatus.LIP_SYNC_GENERATED