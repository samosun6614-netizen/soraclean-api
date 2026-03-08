from flask import Flask, request, jsonify, make_response
import requests
import re
import os

app = Flask(__name__)

def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = '*'
    return response

@app.after_request
def after_request(response):
    return add_cors(response)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
    "Accept": "application/json",
    "Referer": "https://sora.chatgpt.com/",
    "Origin": "https://sora.chatgpt.com",
}

def extract_share_id(url):
    match = re.search(r'/p/(s_[a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    match = re.search(r'(s_[a-zA-Z0-9_-]{10,})', url)
    return match.group(1) if match else None

def find_video_url(data, depth=0):
    if depth > 8:
        return None
    if isinstance(data, str):
        if data.startswith('http') and any(ext in data for ext in ['.mp4', '.webm', '.mov']):
            return data
    if isinstance(data, dict):
        for key in ['video_url', 'url', 'download_url', 'source_url', 'media_url']:
            if key in data:
                result = find_video_url(data[key], depth+1)
                if result:
                    return result
        for value in data.values():
            result = find_video_url(value, depth+1)
            if result:
                return result
    if isinstance(data, list):
        for item in data:
            result = find_video_url(item, depth+1)
            if result:
                return result
    return None

@app.route('/', methods=['GET', 'OPTIONS'])
def index():
    if request.method == 'OPTIONS':
        return make_response('', 200)
    return jsonify({"status": "ok", "service": "SoraClean API"})

@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health():
    if request.method == 'OPTIONS':
        return make_response('', 200)
    return jsonify({"status": "ok"})

@app.route('/api/clean', methods=['POST', 'OPTIONS'])
def clean_video():
    if request.method == 'OPTIONS':
        return make_response('', 200)
    
    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({"success": False, "error": "No URL provided"}), 400
    
    share_id = extract_share_id(url)
    if not share_id:
        return jsonify({"success": False, "error": "Invalid Sora URL"}), 400
    
    endpoints = [
        f"https://sora.chatgpt.com/p/{share_id}.json",
        f"https://sora.chatgpt.com/backend-api/share/{share_id}",
    ]
    
    last_error = "Could not find video"
    for endpoint in endpoints:
        try:
            resp = requests.get(endpoint, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                json_data = resp.json()
                raw_url = find_video_url(json_data)
                if raw_url:
                    clean_url = re.sub(r'_wm(\.(mp4|webm|mov))', r'\1', raw_url, flags=re.IGNORECASE)
                    return jsonify({
                        "success": True,
                        "title": json_data.get('title', 'Sora Video'),
                        "prompt": str(json_data.get('prompt', ''))[:200],
                        "clean_url": clean_url,
                        "watermark_removed": raw_url != clean_url,
                    })
                last_error = "Video URL not found in response"
            else:
                last_error = f"Sora API returned {resp.status_code}"
        except Exception as e:
            last_error = str(e)[:100]
    
    return jsonify({"success": False, "error": last_error}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
                
