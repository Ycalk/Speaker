import base64
import io
import json
import logging
import os
from listeners.base import Listener
import numpy as np
from scipy.io.wavfile import write, read

class VoiceGeneratedListener (Listener):
    
    def __init__(self, storage: str, generating_queue_table: int, channel:str, 
                 queue_name: str, s3):
        
        super().__init__(storage, generating_queue_table, channel)
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.s3 = s3
        self.queue_name = queue_name
        self.audio_temp = os.getenv('audio_data_temp')
        
        os.makedirs(self.audio_temp, exist_ok=True)
        
    def save_audio(self, audio_data, file_id) -> str:
        audio_data = base64.b64decode(audio_data)
        buffer = io.BytesIO(audio_data)
        sample_rate, audio_array = read(buffer)
        safe_path = f'{self.audio_temp}/{file_id}.wav'
        write(safe_path, sample_rate, audio_array)
        
        return safe_path
    
    def upload_audio(self, audio_path, celebrity_code, name):
        try:
            short_code = celebrity_code.split('_')[0]
            self.s3.upload_file(audio_path, os.getenv('GENERATED_BUCKET'), f'voice/{short_code}/{name}.wav')
        
        except Exception as e:
            self.logger.error("An error occurred while uploading the audio: %s", e)
    
    async def handler(self, data : dict):
        if 'audio' not in data:
            self.logger.error("No audio data in the message: %s", data)
            return
        if 'error' in data:
            self.logger.error("Error in the message: %s", data)
            return
        
        try:
            if data['audio'] == 'generated':
                data['audio'] = 'cloud'
                self.logger.info("Voice already generated for user: %s", data['user_name'])
            
            else:
                self.logger.info("Received audio data in voice_generated_queue")
                audio_path = self.save_audio(data['audio'], data['id'])
                data['audio'] = 'cloud'
                self.upload_audio(audio_path, data['celebrity_code'], data['user_name'])
                self.logger.info("Audio was upload: %s", data)
                os.remove(audio_path)
            
            await self._redis.rpush(self.queue_name, json.dumps(data))
        
        except Exception as e:
            self.logger.error("An error occurred while handling the message in voice_generated_queue: %s", e)