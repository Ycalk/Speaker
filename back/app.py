import aiohttp
from quart import Quart, jsonify, request
import json
import re
import os
import aioredis
from time import time

app = Quart(__name__)
NAME_API_URL = os.getenv('NAME_API_URL')
VALIDATE_NAME_TIME_WINDOW = int(os.getenv('VALIDATE_NAME_TIME_WINDOW'))
VALIDATE_NAME_SPAM_THRESHOLD = int(os.getenv('VALIDATE_NAME_SPAM_THRESHOLD'))


with open('utils/config.json', 'r', encoding='utf-8') as config_file:
    config_data = json.load(config_file)

with open('utils/celebrities.json', 'r', encoding='utf-8') as celebrities_file:
    celebrities_data = json.load(celebrities_file)

redis = aioredis.from_url(os.getenv('REDIS_STORAGE'), db=config_data['redis']['generating_queue_table'])
to_generate_key = config_data['redis']['generating_queue_table_keys']['voice']


@app.route('/config', methods=['GET'])
async def get_config():
    try:
        return jsonify(config_data)
    except FileNotFoundError:
        return jsonify({"error": "Config file not found"}), 404
    except Exception as e:
        return jsonify({"error": "Something went wrong", "message": str(e)}), 500

@app.route('/celebrities', methods=['GET'])
async def get_celebrities():
    try:
        return jsonify(celebrities_data)
    except Exception as e:
        return jsonify({"error": "Something went wrong", "message": str(e)}), 500

@app.route('/queue_length', methods=['GET'])
async def get_queue_length():
    return jsonify({"queue_length": await redis.llen(to_generate_key)})


validate_name_request_cache = {}

@app.route('/validate', methods=['POST'])
async def validate():
    global validate_name_request_cache
    
    json_data = await request.get_json()
    name = json_data.get('name')
    user_id = json_data.get('user_id')
    
    if not user_id:
        return jsonify({"valid": False, "gender": "NEUTRAL"}), 400
    
    current_time = time()
    
    validate_name_request_cache = {k: [t for t in v if current_time - t < VALIDATE_NAME_TIME_WINDOW] 
                              for k, v in validate_name_request_cache.items()}
    
    if user_id in validate_name_request_cache and len(validate_name_request_cache[user_id]) >= VALIDATE_NAME_SPAM_THRESHOLD:
        return jsonify({"valid": False, "gender": "NEUTRAL"}), 400
    
    if user_id not in validate_name_request_cache:
        validate_name_request_cache[user_id] = []
    
    is_name, gender = await validate_name(name)
    return jsonify({"valid": is_name, "gender": gender}), 200
    
async def validate_name(name: str) -> tuple[bool, str]:
    def parse_match(data):
        if data['confidence'] > 0.6:
            gender = data['parsedPerson']['gender']
            if gender['confidence'] > 0.6:
                gender = gender['gender']
            else:
                gender = 'NEUTRAL'
            return True, gender
        return False, 'NEUTRAL'
    
    data = {
        "inputPerson" : {
            "type" : "NaturalInputPerson",
            "personName" : {
                "nameFields" : [{
                    "string" : name,
                    "fieldType" : "GIVENNAME"
                }]
            },
        }
    }
    if name.isalpha() and bool(re.fullmatch(r'[а-яА-ЯёЁ]+', name)) and len(name) > 2 and len(name) < config_data["MAX_NAME_LENGTH"]:
        async with aiohttp.ClientSession(headers={"Content-Type": "application/json"}) as session:
            async with session.post(NAME_API_URL, json=data) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'bestMatch' in data:
                        return parse_match(data['bestMatch'])
                    for match in data['matches']:
                        if match['confidence'] > 0.6:
                            return parse_match(match)
    return False, 'NEUTRAL'
                
        

def main():
    app.run(host='localhost', port=5000)