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
        self.vc_request = g.generation_config['voice_changer_request_channel']
        self.vc_response = g.generation_config['voice_changer_response_channel']
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        if self.request['celebrity_code'] in ("vidos_good_1", "vidos_good_2", "vidos_bad"):
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
                
                res = self.voice_change(audio_data)
                if not res:
                    self.__status = VoiceGenerationStatus.FAILED
                    self.request['error'] = "Voice change failed"
            else:
                self.__status = VoiceGenerationStatus.FAILED
                self.logger.error("Voice generation failed with status code: %d, response: %s", response.status_code, response.text)
                self.request['error'] = f"Voice generation failed with status code: {response.status_code}"
        except requests.RequestException as e:
            self.__status = VoiceGenerationStatus.FAILED
            self.logger.error("An error occurred while making the tts request: %s", e)
            self.request['error'] = f"An error occurred while making the tts request: {str(e)}"
        except Exception as e:
            self.__status = VoiceGenerationStatus.FAILED
            self.logger.error("An error occurred: %s", e)
            self.request['error'] = f"An error occurred: {str(e)}"
        finally:
            self.redis.publish(self.return_voice_channel, json.dumps(self.request))
            self.logger.info("Published request to return voice channel: %s", self.return_voice_channel)
    
    def voice_change(self, audio_data):
        try:
            self.logger.info("Changing voice for request: %s", {k: v for k, v in self.request.items() if k != 'audio'})
            self.redis.publish(self.vc_request, json.dumps({"request_id": self.request['id'], 
                                                            "audio": audio_data, 'celebrity_code': self.request['celebrity_code']}))
            pubsub = self.redis.pubsub()
            pubsub.subscribe(self.vc_response)
            response = None
            for message in pubsub.listen():
                if message['type'] == 'message':
                    response = json.loads(message['data'])
                    if response['request_id'] == self.request['id']:
                        break
            
            if response['audio'] != '':
                self.__status = VoiceGenerationStatus.COMPLETED
                self.logger.info("Voice change successful for request: %s", 
                                 {k: v for k, v in self.request.items() if k != 'audio'})
                self.request['voice_changed'] = datetime.datetime.now().isoformat()
                self.request['audio'] = response['audio']
                return True
            else:
                self.__status = VoiceGenerationStatus.FAILED
                self.logger.error("Voice change failed for request: %s", 
                                  {k: v for k, v in self.request.items() if k != 'audio'})
                return False
        except Exception as e:
            self.__status = VoiceGenerationStatus.FAILED
            self.logger.error("An error occurred: %s", e)
            return False