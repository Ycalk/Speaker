import base64
import enum
import json
import logging
import datetime
import time
import requests
import os
from handlers.generator import Generator
from pydub import AudioSegment
from handlers.generator import Update, Error

class _PromptGenerator:
    @staticmethod
    def get_default_prompt() -> dict:
        return {
            "text": "",
            "outputAudioSpec": {
                "containerAudio": {
                    "containerAudioType": "WAV"
                }
            },
            "hints": [{"voice": ""}, {"role": ""}, {"speed": ""}],
            "loudnessNormalizationType": "LUFS"
        }
        
    @staticmethod
    def get_vidos_prompt(name: str) -> dict:
        prompt = _PromptGenerator.get_default_prompt()
        prompt['text'] = f"**{name}**!"
        prompt['hints'][0]['voice'] = "lera"
        prompt['hints'][1]['role'] = "friendly"
        prompt['hints'][2]['speed'] = "1.1"
        return prompt
    
    @staticmethod
    def get_burunov_prompt(name: str) -> dict:
        return _PromptGenerator.get_vidos_prompt(name)
    
    @staticmethod
    def get_musagaliev_prompt(name: str) -> dict:
        return _PromptGenerator.get_vidos_prompt(name)
    
    @staticmethod
    def get_carnaval_prompt(name: str) -> dict:
        prompt = _PromptGenerator.get_default_prompt()
        prompt['text'] = f"**{name}**!"
        prompt['hints'][0]['voice'] = "marina"
        prompt['hints'][1]['role'] = "friendly"
        prompt['hints'][2]['speed'] = "1.1"
        return prompt
    
    @staticmethod
    def get_lebedev_prompt(name: str) -> dict:
        prompt = _PromptGenerator.get_default_prompt()
        prompt['text'] = f"**{name}**!"
        prompt['hints'][0]['voice'] = "filipp"
        prompt['hints'][2]['speed'] = "1.1"
        prompt['hints'].pop(1)
        return prompt
    
    @staticmethod
    def get_shcherbakova_prompt(name: str) -> dict:
        return _PromptGenerator.get_vidos_prompt(name)
        

class VoiceGenerationStatus(enum.Enum):
    CREATED = 0
    GENERATING_VOICE = 1
    VOICE_CHANGE = 2
    COMPLETED = 3
    FAILED = 4

class VoiceGeneration:
    __celebrity_to_model ={
        "vidos_good_v1": "vidos",
        "vidos_good_v2": "vidos",
        "vidos_bad_v1": "vidos",
        "vidos_bad_v2": "vidos",
        "vidos_bad_v3": "vidos",
        "burunov" : "burunov",
        "musagaliev": "musagaliev",
        "carnaval": "carnaval",
        "lebedev": "lebedev",
        "shcherbakova": "shcherbakova"
    }
    
    
    def __init__(self, g : Generator, request: dict):
        self.__status = VoiceGenerationStatus.CREATED
        self.request = request
        self.tts_url = g.generation_config['tts_model_url']
        self.api_key = g.generation_config['api_key']
        self.folder_id = g.generation_config['folder_id']
        self.redis = g.redis
        self.g = g
        self.return_voice_channel = g.generation_config['return_voice_channel']
        self.vc_request = g.generation_config['voice_changer_request_channel']
        self.vc_response = g.generation_config['voice_changer_response_channel']
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        if self.request['celebrity_code'] in ("vidos_good_v1", "vidos_good_v2", 
                                              "vidos_bad_v1", "vidos_bad_v2", "vidos_bad_v3"):
            self.__prompt = _PromptGenerator.get_vidos_prompt(self.request['user_name'])
        elif self.request['celebrity_code'] == "burunov":
            self.__prompt = _PromptGenerator.get_burunov_prompt(self.request['user_name'])
        elif self.request['celebrity_code'] == "musagaliev":
            self.__prompt = _PromptGenerator.get_musagaliev_prompt(self.request['user_name'])
        elif self.request['celebrity_code'] == "carnaval":
            self.__prompt = _PromptGenerator.get_carnaval_prompt(self.request['user_name'])
        elif self.request['celebrity_code'] == "lebedev":
            self.__prompt = _PromptGenerator.get_lebedev_prompt(self.request['user_name'])
        elif self.request['celebrity_code'] == "shcherbakova":
            self.__prompt = _PromptGenerator.get_shcherbakova_prompt(self.request['user_name'])
        
        self.logger.info("Generated prompt %s for user: %s", self.request['celebrity_code'], self.request['user_name'])
        
    @property
    def status(self):
        return self.__status
    
    def add_silence(self, audio_str):
        path = f"{os.getenv('audio_data_temp')}/{self.request['id']}.wav"
        with open(path, "wb") as audio_file:
            audio_file.write(base64.b64decode(audio_str))
        audio = AudioSegment.from_file(path)
        audio_len = len(audio)
        if (audio_len < 1100):
            silence = AudioSegment.silent(duration=1100 - audio_len)
            audio = silence + audio
        save_path = f"{os.getenv('audio_data_temp')}/{self.request['id']}_updated.wav"
        audio.export(save_path, format="wav")
        with open(save_path, "rb") as audio_file:
            res = base64.b64encode(audio_file.read()).decode('utf-8')
        os.remove(save_path)
        os.remove(path)
        return res
    
    def start(self):
        self.request['voice_generation_start'] = datetime.datetime.now().isoformat()
        self.g.send_notification(Update.GENERATION_STARTED,
                                 self.request['user_id'], self.request['app_type'])
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
                
                audio_data = self.add_silence(audio_data)
                self.logger.info("Added silence to audio data for request: %s", 
                                 {k: v for k, v in self.request.items() if k != 'audio'})
                self.g.send_notification(Update.TTS_GENERATED, 
                                         self.request['user_id'], self.request['app_type'])
                res = self.voice_change(audio_data)
                if not res:
                    self.__status = VoiceGenerationStatus.FAILED
                    self.request['error'] = "Voice change failed"
                    self.g.send_notification(Error.VOICE_FAILED,
                                             self.request['user_id'], self.request['app_type'])
                else:
                    self.__status = VoiceGenerationStatus.COMPLETED
                    self.g.send_notification(Update.VOICE_GENERATED,
                                             self.request['user_id'], self.request['app_type'])
            else:
                self.__status = VoiceGenerationStatus.FAILED
                self.logger.error("Voice generation failed with status code: %d, response: %s", response.status_code, response.text)
                self.request['error'] = f"Voice generation failed with status code: {response.status_code}"
                self.g.send_notification(Error.TTS_FAILED,
                                         self.request['user_id'], self.request['app_type'])
        
        except requests.RequestException as e:
            self.__status = VoiceGenerationStatus.FAILED
            self.logger.error("An error occurred while making the tts request: %s", e)
            self.request['error'] = f"An error occurred while making the tts request: {str(e)}"
        
        except Exception as e:
            self.__status = VoiceGenerationStatus.FAILED
            self.logger.error("An error occurred: %s", e)
            self.request['error'] = f"An error occurred: {str(e)}"
        
        finally:
            self.request['voice_generation_end'] = datetime.datetime.now().isoformat()
            self.redis.publish(self.return_voice_channel, json.dumps(self.request))
            self.logger.info("Published request to return voice channel: %s", self.return_voice_channel)
    
    def voice_change(self, audio_data):
        try:
            self.logger.info("Changing voice for request: %s", {k: v for k, v in self.request.items() if k != 'audio'})
            
            self.redis.publish(self.vc_request, json.dumps({
                "request_id": self.request['id'], 
                "audio": audio_data, 
                "model": VoiceGeneration.__celebrity_to_model[self.request['celebrity_code']]
            }))
            
            pubsub = self.redis.pubsub()
            pubsub.subscribe(self.vc_response)
            
            timeout = 120
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                message = pubsub.get_message(timeout=1.0)
                if message and message['type'] == 'message':
                    response = json.loads(message['data'])
                    if response['request_id'] == self.request['id']:
                        if response['audio'] != '':
                            self.__status = VoiceGenerationStatus.COMPLETED
                            self.logger.info("Voice change successful for request: %s", 
                                            {k: v for k, v in self.request.items() if k != 'audio'})
                            self.request['audio'] = response['audio']
                            return True
                        else:
                            break
            self.__status = VoiceGenerationStatus.FAILED
            self.logger.error("Voice change failed for request: %s", 
                            {k: v for k, v in self.request.items() if k != 'audio'})
            return False
        except Exception as e:
            self.__status = VoiceGenerationStatus.FAILED
            self.logger.error("An error occurred: %s", e)
            return False