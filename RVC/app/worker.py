import base64
import io
import json
from multiprocessing import Queue
import numpy as np
from redis import Redis
from scipy.io.wavfile import write
from configs.config import Config
from infer.modules.vc.modules import VC
import logging
import os
import signal

class VoiceChanger:
    infos = {
        'vidos': {
            'model': 'Vidos.pth',
            'index_path': 'logs/Vidos/added_IVF216_Flat_nprobe_1_Vidos_v2.index',
            'pitch': -11,
            'device': 'cpu'
        },
        'burunov': {
            'model': 'Burunov.pth',
            'index_path': 'logs/Burunov/added_IVF772_Flat_nprobe_1_Burunov_v2.index',
            'pitch': -11,
            'device': 'cpu'
        },
        "musagaliev": {
            'model': 'Musagaliev.pth',
            'index_path': 'logs/Musagaliev/added_IVF683_Flat_nprobe_1_Musagaliev_v2.index',
            'pitch': 0,
            'device': 'cpu'
        },
        "carnaval": {
            'model': 'Carnaval.pth',
            'index_path': 'logs/Carnaval/added_IVF685_Flat_nprobe_1_Carnaval_v2.index',
            'pitch': 2,
            'device': 'cpu'
        },
        "lebedev": {
            'model': 'Lebedev.pth',
            'index_path': 'logs/Lebedev/added_IVF689_Flat_nprobe_1_Lebedev_v2.index',
            'pitch': 0,
            'device': 'cpu'
        },
        "shcherbakova": {
            'model': 'Shcherbakova.pth',
            'index_path': 'logs/Shcherbakova/added_IVF683_Flat_nprobe_1_Shcherbakova_v2.index',
            'pitch': 0,
            'device': 'cpu'
        },
        "dorohov": {
            'model': 'Dorohov.pth',
            'index_path': 'logs/Dorohov/added_IVF561_Flat_nprobe_1_Dorohov_v2.index',
            'pitch': 5,
            'device': 'cpu'
        },
        "cross": {
            'model': 'Cross.pth',
            'index_path': 'logs/Cross/added_IVF585_Flat_nprobe_1_Cross_v2.index',
            'pitch': 6,
            'device': 'cpu'
        },
        "chebatkov": {
            'model': 'Chebatkov.pth',
            'index_path': 'logs/Chebatkov/added_IVF50_Flat_nprobe_1_Chebatkov_v2.index',
            'pitch': 0,
            'device': 'cpu'
        }
    }

    @staticmethod
    def encode_wav_to_base64(wav_opt):
        sample_rate, audio_array = wav_opt[0], wav_opt[1]
        buffer = io.BytesIO()
        write(buffer, sample_rate, audio_array)
        buffer.seek(0)
        base64_audio = base64.b64encode(buffer.read()).decode('utf-8')
        return base64_audio

    def __init__(self, model, device: str = "cuda:0"):
        self.config = Config()
        self.config.device = device if device else self.config.device
        self.config.is_half = False
        self.model = model

        self.vc = VC(self.config)
        self.vc.get_vc(VoiceChanger.infos[model]['model'])
        self.logger = logging.getLogger(__name__)

    def run(self, input_path) -> str:
        self.logger.info(f"Running voice change on {input_path}")
        _, wav_opt = self.vc.vc_single(
            0,
            input_path,
            VoiceChanger.infos[self.model]['pitch'],
            None,
            'rmvpe',
            VoiceChanger.infos[self.model]['index_path'],
            None,
            0.5,
            3,
            0,
            0.0,
            0.5,
        )
        return VoiceChanger.encode_wav_to_base64(wav_opt)
    
    @staticmethod
    def create_audio(data, audio_id, audio_temp_root) -> str:
        audio_data = base64.b64decode(data)
        audio_array = np.frombuffer(audio_data[44:], dtype=np.int16)
        sample_rate = 22050
        
        file_name = f"{audio_temp_root}/{audio_id}.wav"
        os.makedirs(audio_temp_root, exist_ok=True)
        write(file_name, sample_rate, audio_array)
        return file_name
    
    @staticmethod
    def start_voice_changer(model, redis_url, return_channel, queue: Queue):
        voice_changer = VoiceChanger(model, device=VoiceChanger.infos[model]['device'])
        signal.signal(signal.SIGTERM, voice_changer.handle_signal)
        signal.signal(signal.SIGINT, voice_changer.handle_signal)
        audio_temp_root = os.getenv('audio_temp_root')
        redis = Redis.from_url(redis_url)
        voice_changer.logger.info(f"Starting voice changer for {model}")
        while True:
            try:
                request_id, audio = queue.get(timeout=60)
            except Exception as e:
                voice_changer.logger.warning(f"No data in queue for model {model}: {e}")
                continue
            voice_changer.logger.info(f"Received request for {request_id} with model {model}")
            if request_id is None and audio is None:
                voice_changer.logger.info(f"Stopping voice changer for {model}")
                break
            audio_file = VoiceChanger.create_audio(audio, request_id, audio_temp_root)
            try:
                generated = voice_changer.run(audio_file)
                voice_changer.logger.info(f"Generated voice for {request_id} with model {model}")
                redis.publish(return_channel, json.dumps({"request_id" : request_id, "audio": generated}))
            except Exception as e:
                voice_changer.logger.error(f"Error processing request {request_id} with model {model}: {e}")
                redis.publish(return_channel, json.dumps({"request_id" : request_id, "audio": ""}))
    
    def handle_signal(self, signum, frame):
        self.logger.info(f"Received signal {signum}, terminating process.")
        exit(0)