import enum
import json
import logging
import datetime
import requests

from handlers.generator import Generator


class _PromptGenerator:
    default_prompt = {
        "text": "",
        "outputAudioSpec": {
            "containerAudio": {
                "containerAudioType": "WAV"
            }
        },
        "hints": [
            {
                "voice": ""
            },
            {
                "role": ""
            },
            {
                "speed": ""
            }
        ],
        "loudnessNormalizationType": "LUFS"
    }
    @staticmethod
    def get_vidos_prompt(name: str) -> dict:
        prompt = _PromptGenerator.default_prompt
        prompt['text'] = f"**{name}**!"
        prompt['hints'][0]['voice'] = "lera"
        prompt['hints'][1]['role'] = "friendly"
        prompt['hints'][2]['speed'] = "1.1"
        return prompt

class VoiceGenerationStatus(enum.Enum):
    CREATED = 0
    GENERATING_VOICE = 1
    VOICE_CHANGE = 2
    COMPLETED = 3
    FAILED = 4

class VoiceGeneration:
    def __init__(self, g : Generator, request: dict):
        self.__status = VoiceGenerationStatus.CREATED
        self.request = request
        self.tts_url = g.generation_config['tts_model_url']
        self.api_key = g.generation_config['api_key']
        self.folder_id = g.generation_config['folder_id']
        self.redis = g.redis
        self.return_voice_channel = g.generation_config['return_voice_channel']
        self.voice_changer_server_path = g.generation_config['voice_changer_server_path']
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        if self.request['celebrity_code'] == "vidos_good":
            self.__prompt = _PromptGenerator.get_vidos_prompt(self.request['user_name'])
            self.logger.info("Generated prompt %s for user: %s", self.request['celebrity_code'], self.request['user_name'])
    
    @property
    def status(self):
        return self.__status
    
    def start(self):
        self.__status = VoiceGenerationStatus.GENERATING_VOICE
        self.logger.info("Starting voice generation for request: %s", self.request)
        
        headers = {
            "authorization": f"Api-key {self.api_key}",
            "x-folder-id": self.folder_id,
        }
        try:
            response = requests.post(self.tts_url, headers=headers, json=self.__prompt)
            if response.status_code == 200:
                self.__status = VoiceGenerationStatus.VOICE_CHANGE
                audio_data = response.json()['result']['audioChunk']['data']
                
                self.logger.info("TTS generation successful for request: %s", 
                                 {k: v for k, v in self.request.items() if k != 'audio'})
                self.request['tts_generated'] = datetime.datetime.now().isoformat()
                
                self.voice_change(audio_data)
            else:
                self.__status = VoiceGenerationStatus.FAILED
                self.logger.error("Voice generation failed with status code: %d, response: %s", response.status_code, response.text)
        except requests.RequestException as e:
            self.__status = VoiceGenerationStatus.FAILED
            self.logger.error("An error occurred while making the request: %s", e)
        except Exception as e:
            self.__status = VoiceGenerationStatus.FAILED
            self.logger.error("An error occurred: %s", e)
        finally:
            self.redis.publish(self.return_voice_channel, json.dumps(self.request))
            self.logger.info("Published request to return voice channel: %s", self.return_voice_channel)
    
    def voice_change(self, audio_data):
        try:
            self.logger.info("Changing voice for request: %s", {k: v for k, v in self.request.items() if k != 'audio'})
            response = requests.post(self.voice_changer_server_path, json={'audio': audio_data, 'celebrity_code': self.request['celebrity_code']})
            if response.status_code == 200:
                self.__status = VoiceGenerationStatus.COMPLETED
                self.logger.info("Voice change successful for request: %s", 
                                 {k: v for k, v in self.request.items() if k != 'audio'})
                self.request['voice_changed'] = datetime.datetime.now().isoformat()
                self.request['audio'] = response.json()['result']
            else:
                self.__status = VoiceGenerationStatus.FAILED
                self.logger.error("Voice change failed with status code: %d, response: %s", response.status_code, response.text)
        except requests.RequestException as e:
            self.__status = VoiceGenerationStatus.FAILED
            self.logger.error("An error occurred while making the request: %s", e)
        except Exception as e:
            self.__status = VoiceGenerationStatus.FAILED
            self.logger.error("An error occurred: %s", e)