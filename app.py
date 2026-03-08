from flask import Flask, request, jsonify, make_response
import requests
import os

app = Flask(__name__)

SORATOOLS_KEY = 'dfd93e3d-6068-4f27-85f3-bbd0d2ed12ce'
SORATOOLS_URL = 'https://sora.thirdme.com/api/v1/remove-watermark'

def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = '*'
    return response

@app.after_request
def after_request(response):
    return add_cors(response)

@app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "ok", "service": "SoraClean API"})

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/api/clean', methods=['POST', 'OPTIONS'])
def clean_video():
    if request.method == 'OPTIONS':
        return make_response('', 200)

    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()

    if not url:
        return jsonify({"success": False, "error": "No URL provided"}), 400

    try:
        res = requests.post(
            SORATOOLS_URL,
            json={"url": url},
            headers={
                "Authorization": f"Bearer {SORATOOLS_KEY}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        data = res.json()
        print("SoraTools response:", data)

        if data.get('status') == 'success' and data.get('data'):
            clean_url = data['data'].get('links', {}).get('mp4NoWatermark') or data['data'].get('url')
            if clean_url:
                return jsonify({"success": True, "clean_url": clean_url})
        
        return jsonify({"success": False, "error": data.get('message', 'Processing failed')}), 400

    except Exception as e:
        return jsonify({"success": False, "error": str(e)[:100]}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
    
