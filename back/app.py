from quart import Quart, jsonify, request
import json

app = Quart(__name__)

@app.route('/config', methods=['GET'])
async def get_config():
    try:
        with open('config.json', 'r') as config_file:
            config_data = json.load(config_file)
            return jsonify(config_data)
    except FileNotFoundError:
        return jsonify({"error": "Config file not found"}), 404
    except Exception as e:
        return jsonify({"error": "Something went wrong", "message": str(e)}), 500

@app.route('/celebrities', methods=['GET'])
async def get_celebrities():
    try:
        return jsonify([{'name': 'Test', 'code': 'test'}])
    except Exception as e:
        return jsonify({"error": "Something went wrong", "message": str(e)}), 500

@app.route('/validate', methods=['POST'])
async def validate():
    data = await request.get_json()
    if await validate_name(data.get('name')):
        return jsonify({"message": "Validation successful"}), 200
    else:
        return jsonify({"error": "Validation failed"}), 400

# TODO request to gpt
async def validate_name(name: str) -> bool:
    return name.isalpha() and len(name) > 3

def main():
    app.run()