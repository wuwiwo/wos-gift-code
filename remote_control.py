from flask import Flask, request, jsonify, render_template
import subprocess
import os
from functools import wraps
from flask import make_response
import json
import shlex


app = Flask(__name__)

# 从 JSON 文件读取配置
config_file = 'config.json'

def load_config():
    try:
       with open(config_file, 'r') as f:
             config = json.load(f)
             return config.get("username"), config.get("password")
    except Exception as e:
        print("Error loading config from config.json:", e)
        return None,None

USERNAME, PASSWORD = load_config()

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
         auth = request.authorization
         if not auth or not (auth.username == USERNAME and auth.password == PASSWORD):
                return  authenticate()
         return f(*args, **kwargs)
    return decorated


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return  make_response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials',
         401,
         {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

ALLOWED_SCRIPTS = ["redeem_code.py"] # 白名单
@app.route('/', methods=['GET'])
@requires_auth
def index():
    return render_template('index.html')


@app.route('/redeem_giftcode', methods=['POST'])
@requires_auth
def redeem_giftcode():
    try:
        data = request.get_json()
        gift_code = data.get('gift_code')

        if not gift_code:
            return jsonify({'error': 'Gift code not provided'}), 400

        gift_code = str(gift_code) # 强制转换为字符串

        # 构建完整的命令
        script_name = "redeem_code.py"
        if script_name not in ALLOWED_SCRIPTS:
           return jsonify({'error': f'Script {script_name} not allowed'}), 403

        command_list = ["python", script_name, "-c", gift_code]
        # 确保 redeem_code.py 在当前目录，否则需要修改路径
        if not os.path.exists(script_name):
            return jsonify({'error': f'{script_name} not found'}), 404

        result = subprocess.run(command_list, capture_output=True, text=True)
        return jsonify({'output': result.stdout, 'error': result.stderr}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)