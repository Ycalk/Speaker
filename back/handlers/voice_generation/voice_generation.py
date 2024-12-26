import base64
import enum
import json
import logging
import datetime
import time
import requests
import os
from handlers.generator import Generator
from pydub import AudioSegment, silence
from handlers.generator import Update, Error
import librosa
import noisereduce as nr
import soundfile as sf


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
        prompt['text'] = f"Привет <[small]> **{name}**! <[small]> **{name.upper()}**!"
        prompt['hints'][0]['voice'] = "lera"
        prompt['hints'][1]['role'] = "friendly"
        prompt['hints'][2]['speed'] = "1.1"
        return prompt
    
    @staticmethod
    def get_burunov_prompt(name: str) -> dict:
        return _PromptGenerator.get_vidos_prompt(name)
    
    @staticmethod
    def get_musagaliev_prompt(name: str) -> dict:
        prompt = _PromptGenerator.get_default_prompt()
        prompt['text'] = f"Привет <[small]> **{name}**! <[small]> **{name.upper()}**!"
        prompt['hints'][0]['voice'] = "alexander"
        prompt['hints'][1]['role'] = "neutral"
        prompt['hints'][2]['speed'] = "1.1"
        return prompt
    
    @staticmethod
    def get_carnaval_prompt(name: str) -> dict:
        prompt = _PromptGenerator.get_default_prompt()
        prompt['text'] = f"Привет <[small]> **{name}**! <[small]> **{name.upper()}**!"
        prompt['hints'][0]['voice'] = "marina"
        prompt['hints'][1]['role'] = "friendly"
        prompt['hints'][2]['speed'] = "1.1"
        return prompt
    
    @staticmethod
    def get_lebedev_prompt(name: str) -> dict:
        prompt = _PromptGenerator.get_default_prompt()
        prompt['text'] = f"Привет <[small]> **{name}**! <[small]> **{name.upper()}**!"
        prompt['hints'][0]['voice'] = "filipp"
        prompt['hints'][2]['speed'] = "1.1"
        prompt['hints'].pop(1)
        return prompt
    
    @staticmethod
    def get_shcherbakova_prompt(name: str) -> dict:
        return _PromptGenerator.get_vidos_prompt(name)
    
    @staticmethod
    def get_dorohov_prompt(name: str) -> dict:
        return _PromptGenerator.get_vidos_prompt(name)

    @staticmethod
    def get_cross_prompt(name: str) -> dict:
        prompt = _PromptGenerator.get_default_prompt()
        prompt['text'] = f"Привет <[small]> **{name}**! <[small]> **{name.upper()}**!"
        prompt['hints'][0]['voice'] = "lera"
        prompt['hints'][1]['role'] = "neutral"
        prompt['hints'][2]['speed'] = "1.1"
        return prompt
    
    def get_chebatkov_prompt(name: str) -> str:
        prompt = _PromptGenerator.get_default_prompt()
        prompt['text'] = f"Привет <[small]> **{name}**! <[small]> **{name.upper()}**!"
        prompt['hints'][0]['voice'] = "ermil"
        prompt['hints'][1]['role'] = "neutral"
        prompt['hints'][2]['speed'] = "1"
        return prompt
    
class VoiceGenerationStatus(enum.Enum):
    CREATED = 0
    GENERATING_VOICE = 1
    VOICE_CHANGE = 2
    COMPLETED = 3
    FAILED = 4

class VoiceGeneration:
    __celebrities_info ={
        "vidos_good_v1": ("vidos", _PromptGenerator.get_vidos_prompt),
        "vidos_good_v2": ("vidos", _PromptGenerator.get_vidos_prompt),
        "vidos_bad_v1": ("vidos", _PromptGenerator.get_vidos_prompt),
        "vidos_bad_v2": ("vidos", _PromptGenerator.get_vidos_prompt),
        "vidos_bad_v3": ("vidos", _PromptGenerator.get_vidos_prompt),
        "burunov" : ("burunov", _PromptGenerator.get_burunov_prompt),
        "musagaliev": ("musagaliev", _PromptGenerator.get_musagaliev_prompt),
        "carnaval": ("carnaval", _PromptGenerator.get_carnaval_prompt),
        "lebedev": ("lebedev", _PromptGenerator.get_lebedev_prompt),
        "shcherbakova": ("shcherbakova", _PromptGenerator.get_shcherbakova_prompt),
        "dorohov": ("dorohov", _PromptGenerator.get_dorohov_prompt),
        "cross": ("cross", _PromptGenerator.get_cross_prompt),
        "chebatkov": ("chebatkov", _PromptGenerator.get_chebatkov_prompt),
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
        
        prompt_generator = VoiceGeneration.__celebrities_info[self.request['celebrity_code']][1]
        self.__prompt = prompt_generator(self.request['user_name'])
        
        self.logger.info("Generated prompt %s for user: %s", self.request['celebrity_code'], self.request['user_name'])
        
    @property
    def status(self):
        return self.__status
    
    def add_silence(self, audio: AudioSegment) -> str:
        audio_len = len(audio)
        if (audio_len < 1100):
            silence = AudioSegment.silent(duration=1100 - audio_len)
            audio = silence + audio
        save_path = f"{os.getenv('audio_data_temp')}/{self.request['id']}_updated.wav"
        audio.export(save_path, format="wav")
        with open(save_path, "rb") as audio_file:
            res = base64.b64encode(audio_file.read()).decode('utf-8')
        os.remove(save_path)
        return res
    
    def get_name_segment(self, audio_str) -> AudioSegment:
        path = f"{os.getenv('audio_data_temp')}/{self.request['id']}.wav"
        with open(path, "wb") as audio_file:
            audio_file.write(base64.b64decode(audio_str))
        audio = AudioSegment.from_file(path)
        
        min_silence_len = 200
        silence_thresh = audio.dBFS - 16
        silences = silence.detect_silence(audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh)
        
        if silences:
            last_pause_end = silences[-2][0]
            os.remove(path)
            return audio[last_pause_end + 150:]
    
    def reduce_noise(self, audio_str, gain_dB=10) -> str:
        audio_file = f"{os.getenv('audio_data_temp')}/{self.request['id']}_noise.wav"
        with open(audio_file, "wb") as file:
            file.write(base64.b64decode(audio_str))
        y, sr = librosa.load(audio_file, sr=None)
        y_denoised = nr.reduce_noise(y=y, sr=sr)
        gain = 10 ** (gain_dB / 20)
        y_louder = y_denoised * gain
        y_louder = librosa.util.normalize(y_louder)
        output_file = f"{os.getenv('audio_data_temp')}/{self.request['id']}_noise_denoised.wav"
        sf.write(output_file, y_louder, sr)
        with open(output_file, "rb") as file:
            res = base64.b64encode(file.read()).decode('utf-8')
        os.remove(audio_file)
        os.remove(output_file)
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
                self.logger.info(f"TTS generation successful for request:\nCelebrity_code: {self.request['celebrity_code']}\nName: {self.request['user_name']}")
                
                self.g.send_notification(Update.TTS_GENERATED, 
                                         self.request['user_id'], self.request['app_type'])
                res = self.voice_change(audio_data)
                if not res:
                    self.__status = VoiceGenerationStatus.FAILED
                    self.request['error'] = "Voice change failed"
                    self.g.send_notification(Error.VOICE_FAILED,
                                             self.request['user_id'], self.request['app_type'])
                else:
                    try:
                        name_segment = self.get_name_segment(self.request['audio'])
                        self.request['audio'] = self.add_silence(name_segment)
                        if self.request['celebrity_code'] in ('cross'):
                            self.request['audio'] = self.reduce_noise(self.request['audio'])
                        self.__status = VoiceGenerationStatus.COMPLETED
                        self.g.send_notification(Update.VOICE_GENERATED,
                                                self.request['user_id'], self.request['app_type'])
                        self.logger.info(f"Voice generation successful for request: \nCelebrity_code: {self.request['celebrity_code']}\nName: {self.request['user_name']}")
                    except Exception as e:
                        self.__status = VoiceGenerationStatus.FAILED
                        self.logger.error("An error occurred: %s", e)
                        self.request['error'] = f"An error occurred: {str(e)}"
                        self.g.send_notification(Error.TTS_FAILED,
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
                "model": VoiceGeneration.__celebrities_info[self.request['celebrity_code']][0]
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