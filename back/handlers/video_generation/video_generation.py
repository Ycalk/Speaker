import enum
import json
import logging
import datetime
import os
import time
import numpy as np
import requests
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips

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
        self.return_video_channel = g.generation_config['return_video_channel']
        
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
            save_path = f"{os.getenv('video_data_temp')}/{self.request['id']}_lp.mp4"
            with open(save_path, "wb") as f:
                response = requests.get(video_url)
                f.write(response.content)     
            return save_path
        except Exception as e:
            self.logger.error("An error occurred while creating lip sync: %s", e)
            return 
    
    def normalize_audio(self, video1 : VideoFileClip, video2 : VideoFileClip):
        short_audio1 = video1.set_duration(2).audio
        short_audio2 = video2.set_duration(2).audio
        
        audio1_rms = np.sqrt(np.mean(short_audio1.to_soundarray(fps=22050)**2))
        audio2_rms = np.sqrt(np.mean(short_audio2.to_soundarray(fps=22050)**2))
        target_rms = audio1_rms
        return (video1.set_audio(video1.audio.volumex(target_rms / audio1_rms)),
                video2.set_audio(video2.audio.volumex(target_rms / audio2_rms)))

    def concatenate_videos(self, video1_path, video2_path, output_path):
        video1 = VideoFileClip(video1_path)
        video2 = VideoFileClip(video2_path)

        video1, video2 = self.normalize_audio(video1, video2)
        
        final_video = concatenate_videoclips([video1, video2], method="compose")
        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")
        
    @property
    def status(self):
        return self.__status
    
    def start(self):
        self.request['video_generation_start'] = datetime.datetime.now().isoformat()
        self.logger.info("Starting video generation for request: %s", self.request)
        lip_sync_path = self.create_lip_sync()
        if lip_sync_path:
            self.__status = VideoGenerationStatus.LIP_SYNC_GENERATED
            self.logger.info("Lip sync created successfully for request: %s", self.request)
            self.logger.info("Concatenating videos ...")
            final_video_path = f"{os.getenv('video_data_temp')}/{self.request['id']}_final.mp4"
            self.concatenate_videos(lip_sync_path, 
                                    f"handlers/video_generation/data/{self.request['celebrity_code'].replace('_', '/')}/part2.mp4",
                                    final_video_path)
            self.request['video_generated'] = datetime.datetime.now().isoformat()
            self.__status = VideoGenerationStatus.COMPLETED
            self.request['video'] = final_video_path
            self.redis.publish(self.return_video_channel, json.dumps(self.request))