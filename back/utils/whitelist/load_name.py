import csv
import os
import redis as r
import json

def load_names(config_data, file_path):
    redis = r.Redis.from_url(os.getenv('REDIS_STORAGE'), db=config_data['redis']['saved_names_table'])
    unique_names = set()
    with open(file_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
            unique_names.update([i for i in row if i != ''])
    
    for name in unique_names:
        redis.set(name, json.dumps({'valid': True, 'gender': 'NEUTRAL'}))
    
    redis.set('Степа', json.dumps({'valid': True, 'gender': 'MALE'}))
    