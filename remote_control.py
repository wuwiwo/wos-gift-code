from flask import Flask, request, jsonify, render_template
import subprocess
import os
from functools import wraps
from flask import make_response
import json
import shlex
import requests
import logging
from datetime import datetime

app = Flask(__name__)

# 配置日志
log_file = 'webhook.log'
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# 从 JSON 文件读取配置
config_file = 'config.json'

def load_config():
    try:
       with open(config_file, 'r') as f:
             config = json.load(f)
             return config.get("username"), config.get("password"), config.get("webhook_url")
    except Exception as e:
        logging.error(f"Error loading config from config.json: {e}")
        return None,None,None

USERNAME, PASSWORD, WEBHOOK_URL = load_config()

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
        restart = data.get('restart', False)


        if not gift_code:
            logging.warning("✅ Gift code not provided in request")
            return jsonify({'error': 'Gift code not provided'}), 400

        gift_code = str(gift_code) # 强制转换为字符串

        # 构建完整的命令
        script_name = "redeem_code.py"
        if script_name not in ALLOWED_SCRIPTS:
            logging.warning(f"Script {script_name} not allowed")
            return jsonify({'error': f'Script {script_name} not allowed'}), 403
        command_list = ["python", script_name, "-c", gift_code]
        if restart:
            command_list.append("--restart")
        # 确保 redeem_code.py 在当前目录，否则需要修改路径
        if not os.path.exists(script_name):
            logging.error(f"{script_name} not found")
            return jsonify({'error': f'{script_name} not found'}), 404

        result = subprocess.run(command_list, capture_output=True, text=True)

        # 解析 redeem_code.py 输出结果, 获得统计信息
        output_text = result.stdout
        successful_count = 0
        already_claimed_count = 0
        error_count = 0
        if output_text:
            lines = output_text.split("\n")
            for line in lines:
               if "Successfully claimed gift code for" in line:
                  parts = line.split("Successfully claimed gift code for ")
                  if len(parts) > 1:
                       successful_count = int(parts[1].split(" ")[0])
               elif "had already claimed their gift." in line:
                   parts = line.split(" had already claimed their gift.")
                   if len(parts) > 1:
                        already_claimed_count = int(parts[0].split(" ")[-1])
               elif "Errors ocurred for" in line:
                     parts = line.split("Errors ocurred for ")
                     if len(parts) > 1:
                          error_count = int(parts[1].split(" ")[0])
        # 发送消息到 Webhook
        if WEBHOOK_URL:
            try:
                message = "Gift Code Redemption Completed\n"
                message += f"> Gift code：`{gift_code}`\n"
                message += f"> Successfully claimed: {successful_count}\n"
                message += f"> Already claimed: {already_claimed_count}\n"
                message += f"> Errors: {error_count}"

                data = {"content": message}
                response = requests.post(WEBHOOK_URL, json=data)
                if response.status_code == 200 or response.status_code == 204:
                    logging.info("Message sent to Webhook successfully!")
                else:
                    logging.error(f"Failed to send message to Webhook: {response.status_code}, {response.text}")
            except Exception as e:
                logging.error(f"Failed to send webhook message: {e}")
        return jsonify({'output': result.stdout, 'error': result.stderr}), 200

    except Exception as e:
        logging.error(f"Error in redeem_giftcode: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)