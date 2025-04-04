import logging
from handlers.generator import Error, Generator
import json
import os


from handlers.voice_generation.voice_generation import VoiceGeneration, VoiceGenerationStatus

class VoiceGenerator(Generator):
    __max_threads = int(os.getenv('VOICE_CHANGE_WORKERS'))
    
    def __init__(self, redis_storage, table: int, queue_name: str, tts_model_url: str, 
                 api_key: str, folder_id: str, return_voice_channel: str, 
                 voice_changer_request_channel: str, voice_changer_response_channel: str,
                 notification_channel: str):
        logging.basicConfig(level=logging.INFO)
        
        generation_config = {
            'tts_model_url': tts_model_url,
            'api_key': api_key,
            'folder_id': folder_id,
            'return_voice_channel': return_voice_channel,
            'voice_changer_request_channel': voice_changer_request_channel,
            'voice_changer_response_channel' : voice_changer_response_channel
        }
        
        super().__init__(redis_storage, generation_config, table, queue_name, VoiceGenerator.__max_threads,
                         notification_channel)
        
        self.logger = logging.getLogger(__name__)
    
    def _start_generating(self, message):
        self.logger.info("Starting voice generation for message: %s", message)
        
        try:
            new_generation = VoiceGeneration(self, json.loads(message))
            new_generation.start()
        
        except json.JSONDecodeError as e:
            self.logger.error("Failed to decode JSON message: %s", e)
        
        except Exception as e:
            data = json.loads(message)
            super().send_notification(Error.CANNOT_START, data['user_id'], data['app_type'])
            self.logger.error("An error occurred while starting voice generation: %s", e)