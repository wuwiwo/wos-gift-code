from flask import Flask, request, jsonify, render_template
from functools import wraps
import subprocess
import os
import json
import logging
import shlex
import hmac
import requests
import re

app = Flask(__name__)

# 配置日志
logging.basicConfig(
    filename='webhook.log',
    level=logging.DEBUG,  # 调整为DEBUG级别
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 加载基础配置
CONFIG_FILE = 'config.json'

def load_config():
    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)
            return (
                config.get("username"),
                config.get("password"),
                config.get("webhook_url")
            )
    except Exception as e:
        logger.error(f"配置加载失败: {str(e)}")
        return None, None, None

USERNAME, PASSWORD, WEBHOOK_URL = load_config()

# ================== 认证模块 ==================
def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_credentials(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

def check_credentials(username: str, password: str) -> bool:
    return (
        hmac.compare_digest(username, USERNAME) and
        hmac.compare_digest(password, PASSWORD)
    )

def authenticate():
    return (
        'Authentication Required',
        401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

# ================== 路由模块 ==================
@app.route('/')
@requires_auth
def index():
    return render_template('index.html')

@app.route('/redeem_giftcode', methods=['POST'])
@requires_auth
def redeem_giftcode():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '需要JSON数据'}), 400

        gift_code = str(data.get('gift_code', '')).strip()
        if not gift_code or len(gift_code) > 20:
            return jsonify({'error': '无效的礼品码'}), 400

        result = execute_script(gift_code, data.get('restart', False))
        logger.debug(f"脚本输出: {result.stdout}")
        logger.debug(f"脚本错误: {result.stderr}")

        stats = parse_script_output(result.stdout)
        
        if WEBHOOK_URL:
            send_webhook_notification(gift_code, stats)

        return jsonify({
            'success': True,
            'stats': stats,
            'output': result.stdout,
            'error': result.stderr
        }), 200

    except subprocess.TimeoutExpired as e:
        logger.error(f"执行超时: {str(e)}")
        return jsonify({'error': '处理超时'}), 504
    except FileNotFoundError as e:
        logger.error(f"文件未找到: {str(e)}")
        return jsonify({'error': '系统配置错误'}), 500
    except Exception as e:
        logger.error(f"服务器错误: {str(e)}", exc_info=True)
        return jsonify({'error': '服务器内部错误'}), 500

# ================== 功能模块 ==================
def execute_script(gift_code: str, restart: bool) -> subprocess.CompletedProcess:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(current_dir, 'redeem_code.py')
    results_path = os.path.join(current_dir, 'results.json')

    if not os.path.exists(script_path):
        raise FileNotFoundError(f"兑换脚本不存在: {script_path}")

    cmd = [
        'python', 
        script_path,
        '-c', shlex.quote(gift_code),
        '--results-file', results_path
    ]
    if restart:
        cmd.append('--restart')

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600
    )

def parse_script_output(output: str) -> dict:
    stats = {'success': 0, 'already_claimed': 0, 'errors': 0}
    for line in output.split('\n'):
        # 匹配成功兑换的数值
        success_match = re.search(r'成功兑换.*?: (\d+)', line)
        if success_match:
            stats['success'] = int(success_match.group(1))
        
        # 匹配已兑换的数值
        already_match = re.search(r'已兑换.*?: (\d+)', line)
        if already_match:
            stats['already_claimed'] = int(already_match.group(1))
        
        # 匹配错误的数值
        error_match = re.search(r'错误.*?: (\d+)', line)
        if error_match:
            stats['errors'] = int(error_match.group(1))
    return stats
def send_webhook_notification(gift_code: str, stats: dict):
    try:
        message = (
            "🎮 Gift Code Redemption Completed\n"
            f"> 礼品码 / Code: `{gift_code}`\n"
            f"> ✅ 新成功 / New Success: {stats['success']}\n"
            f"> ☑️ 已兑换 / Already Claimed: {stats['already_claimed']}\n"
            f"> 🚫 错误 / Errors: {stats['errors']}"
        )
        response = requests.post(WEBHOOK_URL, json={'content': message}, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Webhook发送失败: {str(e)}")
    except Exception as e:
        logger.error(f"未知错误: {str(e)}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)