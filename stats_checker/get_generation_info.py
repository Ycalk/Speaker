import redis as r
import csv
import json
import os
from dotenv import load_dotenv
from boto3 import Session
from datetime import datetime

load_dotenv()


class InfoGetter:
    def __init__(self):
        url = os.getenv("REDIS_URL")
        yc_static_key_id = os.getenv('YC_STATIC_KEY_ID')
        yc_static_key = os.getenv('YC_STATIC_KEY')
        storage_url = os.getenv('STORAGE_URL')
        
        
        session = Session(
            aws_access_key_id=yc_static_key_id,
            aws_secret_access_key=yc_static_key,
            region_name='ru-central1'
        )
        
        self.bucket = os.getenv('BUCKET')
        self.s3 = session.client(service_name='s3', endpoint_url=storage_url)
        self.redis = r.from_url(url)
        self.unused_keys = ['id', 'app_type', 'video', 'audio', 'behavior']
        self.columns = ["user_id", "celebrity_code", "user_name", "gender", "request_received", "voice_generation_start", "voice_generation_end", "video_generation_start", "video_generation_end", "request_completed"]
    
    def get_generation_info(self, output_path:str):
        keys = self.redis.keys()
        with open(output_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=self.columns)
            writer.writeheader()
            for key in keys:
                info = json.loads(self.redis.get(key).decode('utf-8'))
                for field in self.columns:
                    if field not in info:
                        info[field] = None
                for k in self.unused_keys:
                    if k in info:
                        info.pop(k)
                writer.writerow(info)
    
    def upload(self, path):
        self.s3.upload_file(path, self.bucket, f"{datetime.now().isoformat()}.csv")