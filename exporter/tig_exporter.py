from flask import Flask, Response
from prometheus_client import Gauge, CollectorRegistry, generate_latest, start_http_server
import requests
from datetime import timedelta
import logging
import os
import sys
from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv(dotenv_path=os.getenv('SETTINGS_FILE', '/app/settings.env'))

PLAYER_IDS = [player_id.strip().lower() for player_id in os.getenv('PLAYER_IDS', '').split(',')]
INNOVATOR_IDS = [innovator_id.strip().lower() for innovator_id in os.getenv('INNOVATOR_IDS', '').split(',')]

if not PLAYER_IDS or not INNOVATOR_IDS:
    print("Error: PLAYER_IDS and INNOVATOR_IDS cannot be empty or missing.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

registry = CollectorRegistry()
block_metric = Gauge('tig_block_info', 'Block information', ['round', 'metric'], registry=registry)
player_metric = Gauge('tig_player_data', 'Player data per block', ['round', 'player_id', 'metric'], registry=registry)
innovator_metric = Gauge('tig_innovator_data', 'Innovator data per block', ['round', 'player_id', 'metric'], registry=registry)
challenge_metric = Gauge('tig_challenge_data', 'Challenge data per player', ['round', 'player_id', 'metric', 'challenge_id', 'challenge_name'], registry=registry)
algorithm_metric = Gauge('tig_algorithm_data', 'Algorithm data per player', ['round', 'player_id', 'metric', 'algorithm_id', 'algorithm_name'], registry=registry)

def get_json_response(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        return None

def get_last_block():
    url = "https://mainnet-api.tig.foundation/get-block"
    return get_json_response(url)

def get_price_data():
    url = "https://api.dexscreener.com/latest/dex/pairs/base/0x5280d5e63b416277d0f81fae54bb1e0444cabdaa"
    return get_json_response(url)

def get_players(block_id, player_type="benchmarker"):
    url = f"https://mainnet-api.tig.foundation/get-players?block_id={block_id}&player_type={player_type}"
    data = get_json_response(url)
    return data.get('players', []) if data else []

def get_algorithms(block_id):
    url = f"https://mainnet-api.tig.foundation/get-algorithms?block_id={block_id}"
    data = get_json_response(url)
    return data.get('algorithms', []) if data else []

def get_challenges(block_id):
    url = f"https://mainnet-api.tig.foundation/get-challenges?block_id={block_id}"
    data = get_json_response(url)
    challenges = {}
    if data and "challenges" in data:
        for challenge in data["challenges"]:
            challenges[challenge["id"]] = challenge["details"].get("name", "unknown")
    return challenges

def filter_and_record_metrics(last_block, price_data, players_data, innovators_data, algorithms_data, challenges):
    player_ids = {player_id.lower(): player_id for player_id in PLAYER_IDS}
    innovator_ids = {innovator_id.lower(): innovator_id for innovator_id in INNOVATOR_IDS}

    round_number = last_block.get('block', {}).get('details', {}).get('round', 0)
    latest_block_height = int(last_block.get('block', {}).get('details', {}).get('height', 0))
    blocks_per_round = int(last_block.get('block', {}).get('config', {}).get('rounds', {}).get('blocks_per_round', 0))

    round_start_block = (latest_block_height // blocks_per_round) * blocks_per_round
    round_end_block = round_start_block + blocks_per_round - 1
    round_blocks_left = round_end_block - latest_block_height

    block_metric.labels(round=round_number, metric='priceUsd').set(price_data.get('pair', {}).get('priceUsd', 0))
    block_metric.labels(round=round_number, metric='priceVolume').set(price_data.get('pair', {}).get('volume', {}).get('h24', 0))
    block_metric.labels(round=round_number, metric='priceChange').set(price_data.get('pair', {}).get('priceChange', {}).get('h24', 0))
    block_metric.labels(round=round_number, metric='priceLiquidity').set(float(price_data.get('pair', {}).get('liquidity', {}).get('usd', 0)))
        
    block_metric.labels(round=round_number, metric='height').set(latest_block_height)
    block_metric.labels(round=round_number, metric='round').set(round_number)
    block_metric.labels(round=round_number, metric='blocks_per_round').set(blocks_per_round)
    block_metric.labels(round=round_number, metric='round_start_block').set(round_start_block)
    block_metric.labels(round=round_number, metric='round_end_block').set(round_end_block)
    block_metric.labels(round=round_number, metric='round_blocks_left').set(round_blocks_left)
    block_metric.labels(round=round_number, metric='rewards').set(last_block.get('block', {}).get('config', {}).get('rewards', {}).get('schedule', {})[1].get('block_reward', 0))

    for player in players_data:
        player_id = player.get('id', '').lower()
        if player_id in player_ids:
            block_data = player.get('block_data', {})
            if block_data and block_data.items():
                for key, value in block_data.items():
                    if value:
                        if key == 'num_qualifiers_by_challenge':
                            for challenge_id, num_qualifiers in value.items():
                                challenge_name = challenges.get(challenge_id, "unknown")
                                challenge_metric.labels(
                                    round=round_number,
                                    player_id=player_id,
                                    metric='num_qualifiers_by_challenge',
                                    challenge_id=challenge_id, 
                                    challenge_name=challenge_name
                                ).set(num_qualifiers)
                        elif key == 'cutoff':
                            player_metric.labels(round=round_number, player_id=player_id, metric=key).set(value)
                        else:
                            converted_value = 0
                            if isinstance(value, str):
                                try:
                                    converted_value = float(value) / 1e18
                                except ValueError:
                                    converted_value = 0
                            player_metric.labels(round=round_number, player_id=player_id, metric=key).set(converted_value)
    
    for innovator in innovators_data:
        innovator_id = innovator.get('id', '').lower()
        if innovator_id in innovator_ids:
            block_data = innovator.get('block_data', {})
            if block_data and block_data.items():
                for key, value in block_data.items():
                    if value:
                        converted_value = 0
                        if isinstance(value, str):
                            try:
                                converted_value = float(value) / 1e18
                            except ValueError:
                                converted_value = 0
                        logger.info(f"Add for player {innovator_id} key {key} value {converted_value}")
                        innovator_metric.labels(round=round_number, player_id=innovator_id, metric=key).set(converted_value)

    for algo in algorithms_data:
        algo_id = algo.get('id')
        algo_name = algo.get('details', {}).get('name')
        block_data = algo.get('block_data', {})

        if block_data:
            num_qualifiers_by_player = block_data.get('num_qualifiers_by_player', {})
            for player_id, num_qualifiers in num_qualifiers_by_player.items():
                if player_id in player_ids:
                    algorithm_metric.labels(round=round_number, player_id=player_id, metric='num_qualifiers_by_algo', algorithm_id=algo_id, algorithm_name=algo_name).set(num_qualifiers)

@app.route('/metrics')
def metrics():
    last_block = get_last_block()
    if last_block:
        last_block_id = last_block.get('block', {}).get('id')
        if last_block_id:
            price_data = get_price_data()
            if price_data:
                players_data = get_players(last_block_id)
                innovators_data = get_players(last_block_id, player_type="innovator")
                algorithms_data = get_algorithms(last_block_id)
                challenges = get_challenges(last_block_id)
                
                if players_data and algorithms_data and challenges:
                    filter_and_record_metrics(last_block, price_data, players_data, innovators_data, algorithms_data, challenges)
                else:
                    logger.error("Failed to retrieve players, algorithms, or challenges data")
            else:
                logger.error("Failed to retrieve price data")        
        else:
            logger.error("Failed to retrieve the last block id")
    else:
        logger.error("Failed to retrieve the last block")

    return Response(generate_latest(registry), mimetype='text/plain')

if __name__ == '__main__':
    start_http_server(8001)
    app.run(host='0.0.0.0', port=5002)