from flask import Flask, request, jsonify, make_response
import requests
import os

app = Flask(__name__)

SORATOOLS_KEY = 'dfd93e3d-6068-4f27-85f3-bbd0d2ed12ce'

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

    try:
        res = requests.post(
            'https://sora.thirdme.com/api/v1/remove-watermark',
            json={"url": url},
            headers={
                "Authorization": f"Bearer {SORATOOLS_KEY}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        # Return full response for debugging
        raw = res.json()
        print("SoraTools full response:", raw)
        print("Status code:", res.status_code)
        
        # Try to find clean URL anywhere in response
        if res.status_code == 200:
            d = raw.get('data', {})
            links = d.get('links', {})
            clean_url = (
                links.get('mp4NoWatermark') or
                links.get('mp4') or
                d.get('url') or
                raw.get('url')
            )
            if clean_url:
                return jsonify({"success": True, "clean_url": clean_url})
        
        # Return full response so frontend can show it
        return jsonify({
            "success": False, 
            "error": str(raw),
            "status_code": res.status_code
        }), 400

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
        
