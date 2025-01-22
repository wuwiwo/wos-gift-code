"""
This script redeems gift codes for players of the mobile game Whiteout Survival via their API.
It handles progress tracking and resumption capabilities to avoid reprocessing players.
"""

import argparse
import hashlib
import json
import sys
import time
from os.path import exists
from typing import Dict, List

import requests
from requests.adapters import HTTPAdapter, Retry
from requests.sessions import Session

# Constants
API_URL = "https://wos-giftcode-api.centurygame.com/api"
API_SALT = "tB87#kPtkxqOS2"
HEADERS = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
STATUS_SUCCESS = "Successful"
STATUS_FAILURE = "Unsuccessful"
SAVE_INTERVAL = 10  # Save progress every 10 players processed


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Redeem gift codes for Whiteout Survival players",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-c", "--code", required=True, help="Gift code to redeem")
    parser.add_argument("-f", "--player-file", default="player.json", 
                      help="JSON file containing player data")
    parser.add_argument("-r", "--results-file", default="results.json",
                      help="File to track redemption results")
    parser.add_argument("--restart", action="store_true",
                      help="Force reprocess all players regardless of previous results")
    return parser.parse_args()


def load_json_file(filename: str) -> List[Dict]:
    """Load data from a JSON file."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        if filename == "results.json":
            return []  # Results file is optional
        print(f"Error: Required file {filename} not found!")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {filename}!")
        sys.exit(1)


def save_results(data: List[Dict], filename: str) -> None:
    """Save results to JSON file."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def create_http_session() -> Session:
    """Create configured HTTP session with retry policy."""
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session


def generate_signature(params: List[tuple], salt: str) -> str:
    """Generate MD5 signature for API requests."""
    param_str = "&".join([f"{k}={v}" for k, v in params])
    return hashlib.md5(f"{param_str}{salt}".encode()).hexdigest()


def process_player(player: Dict, code: str, session: Session, result: Dict, counters: Dict) -> None:
    """Process gift code redemption for a single player."""
    player_id = player["id"]
    
    # Skip already processed players unless restart flag is set
    if not args.restart and result["status"].get(player_id) == STATUS_SUCCESS:
        counters["already_claimed"] += 1
        return

    # Prepare login request
    timestamp = time.time_ns()
    login_params = [
        ("fid", player_id),
        ("time", timestamp),
    ]
    login_data = {
        "fid": player_id,
        "time": timestamp,
        "sign": generate_signature(login_params, API_SALT),
    }

    # Execute login
    try:
        login_response = session.post(f"{API_URL}/player", data=login_data, headers=HEADERS, timeout=30)
        login_response.raise_for_status()
        if login_response.json().get("msg") != "success":
            raise requests.exceptions.RequestException("Login failed")
    except Exception as e:
        print(f"\nLogin failed for {player['original_name']} ({player_id}): {str(e)}")
        counters["errors"] += 1
        return

    # Prepare redemption request
    redeem_params = [
        ("cdk", code),
        ("fid", player_id),
        ("time", timestamp),
    ]
    redeem_data = {
        "cdk": code,
        "fid": player_id,
        "time": timestamp,
        "sign": generate_signature(redeem_params, API_SALT),
    }

    # Execute redemption
    try:
        redeem_response = session.post(f"{API_URL}/gift_code", data=redeem_data, headers=HEADERS, timeout=30)
        redeem_response.raise_for_status()
        response_data = redeem_response.json()
    except Exception as e:
        print(f"\nRedemption failed for {player['original_name']} ({player_id}): {str(e)}")
        counters["errors"] += 1
        result["status"][player_id] = STATUS_FAILURE
        return

    # Handle API response codes
    error_code = response_data.get("err_code")
    if error_code == 20000:
        counters["success"] += 1
        result["status"][player_id] = STATUS_SUCCESS
    elif error_code == 40008:
        counters["already_claimed"] += 1
        result["status"][player_id] = STATUS_SUCCESS
    elif error_code in (40014, 40007):
        print(f"\nFatal error: {response_data.get('msg', 'Invalid code')}")
        sys.exit(1)
    else:
        counters["errors"] += 1
        result["status"][player_id] = STATUS_FAILURE
        print(f"\nUnexpected response for {player['original_name']}: {response_data}")


def main():
    """Main execution flow."""
    global args  # pylint: disable=global-variable-undefined
    args = parse_args()
    
    # Initialize data stores
    players = load_json_file(args.player_file)
    all_results = load_json_file(args.results_file)
    
    # Find or create entry for current code
    result_entry = next((r for r in all_results if r["code"] == args.code), None)
    if not result_entry:
        result_entry = {"code": args.code, "status": {}}
        all_results.append(result_entry)
    
    # Initialize counters
    counters = {
        "success": 0,
        "already_claimed": 0,
        "errors": 0
    }

    session = create_http_session()
    total_players = len(players)
    
    print(f"Processing {total_players} players for code: {args.code}")
    
    try:
        for idx, player in enumerate(players, 1):
            # Print progress with clean output
            print(f"Processing {idx}/{total_players}: {player['original_name']}".ljust(80), end="\r")
            
            process_player(player, args.code, session, result_entry, counters)
            
            # Periodic save
            if idx % SAVE_INTERVAL == 0:
                save_results(all_results, args.results_file)
    finally:
        # Final save to capture any remaining changes
        save_results(all_results, args.results_file)
    
    # Print summary (修复此处变量名)
    print(
        f"\n成功兑换 / Successfully claimed: {counters['success']}"
        f"\n已兑换 / Already claimed: {counters['already_claimed']}"
        f"\n错误 / Errors: {counters['errors']}"
    )

if __name__ == "__main__":
    main()