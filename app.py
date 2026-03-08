from flask import Flask, request, jsonify, make_response
import requests
import os
import time

app = Flask(__name__)

KIE_API_KEY = '02bb475bbaea1aac304c2c8c942914f9'
KIE_BASE = 'https://api.kie.ai/api/v1'

def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = '*'
    return response

@app.after_request
def after_request(response):
    return add_cors(response)

@app.route('/')
def index():
    return jsonify({"status": "ok"})

@app.route('/api/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/api/clean', methods=['POST', 'OPTIONS'])
def clean_video():
    if request.method == 'OPTIONS':
        return make_response('', 200)

    body = request.get_json(silent=True) or {}
    url = body.get('url', '').strip()

    if not url:
        return jsonify({"success": False, "error": "No URL provided"}), 400

    headers = {
        "Authorization": f"Bearer {KIE_API_KEY}",
        "Content-Type": "application/json"
    }

    # Step 1: Create task
    try:
        res = requests.post(
            f"{KIE_BASE}/jobs/createTask",
            json={
                "model": "sora-watermark-remover",
                "input": {
                    "video_url": url,
                    "upload_method": "s3"
                }
            },
            headers=headers,
            timeout=30
        )
        data = res.json()
        print("Create task response:", data)

        if data.get('code') != 200:
            return jsonify({"success": False, "error": data.get('message', 'Task creation failed')}), 400

        task_id = data['data']['taskId']
        print("Task ID:", task_id)

    except Exception as e:
        return jsonify({"success": False, "error": f"Create task error: {str(e)}"}), 500

    # Step 2: Poll for result
    for i in range(20):
        time.sleep(3)
        try:
            res = requests.get(
                f"{KIE_BASE}/jobs/task/{task_id}",
                headers=headers,
                timeout=15
            )
            poll = res.json()
            print(f"Poll {i+1}:", poll)

            task_data = poll.get('data', {})
            state = task_data.get('state', '')

            if state == 'success':
                import json
                result_json = task_data.get('resultJson', '{}')
                if isinstance(result_json, str):
                    result_json = json.loads(result_json)
                urls = result_json.get('resultUrls', [])
                if urls:
                    return jsonify({"success": True, "clean_url": urls[0]})
                return jsonify({"success": False, "error": "No video URL in result"}), 400

            elif state == 'fail':
                return jsonify({"success": False, "error": task_data.get('failMsg', 'Task failed')}), 400

        except Exception as e:
            print(f"Poll error: {e}")
            continue

    return jsonify({"success": False, "error": "Timeout — task took too long"}), 408

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
