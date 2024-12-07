import base64
import io
import json
import logging
from listeners.base import Listener
import uuid
import datetime
import numpy as np
from scipy.io.wavfile import write, read

class VoiceGeneratedListener (Listener):
    
    def __init__(self, storage: str, generating_queue_table: int, channel:str, queue_name: str):
        super().__init__(storage, generating_queue_table, channel)
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    async def handler(self, data : dict):
        if 'audio' not in data:
            self.logger.error("No audio data in the message: %s", data)
            return
        if 'error' in data:
            self.logger.error("Error in the message: %s", data)
            return
        try:
            self.logger.info("Received audio data in voice_generated_queue")
            audio_data = base64.b64decode(data['audio'])
            buffer = io.BytesIO(audio_data)
            sample_rate, audio_array = read(buffer)
            write('output.wav', sample_rate, audio_array)
            data['audio'] = 'output.wav'
            self.logger.info("Received data: %s", data)
        except Exception as e:
            self.logger.error("An error occurred while handling the message in voice_generated_queue: %s", e)