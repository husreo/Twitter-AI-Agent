from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import asyncio
from dotenv import load_dotenv
from src.experts import SportsExpert, FoodExpert, AIExpert, SudoStarExpert
from src.core.expert_selector import ExpertSelector
from src.utils.config import ConfigLoader

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

try:
    # Initialize expert system
    config = ConfigLoader.load_config()
    sports_expert = SportsExpert(config)
    food_expert = FoodExpert(config)
    ai_expert = AIExpert(config)
    sudostar_expert = SudoStarExpert(config)
    expert_selector = ExpertSelector()
except Exception as e:
    print(f"Error initializing expert system: {str(e)}")
    # Set default values
    sports_expert = None
    food_expert = None
    ai_expert = None
    sudostar_expert = None
    expert_selector = None

# Telegram bot is temporarily disabled
telegram_status = 'disabled'

@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'version': '1.0.0',
        'endpoints': {
            'ask': '/ask (POST) - Get expert response',
            'health': '/health (GET) - Check system health'
        }
    })

@app.route('/health')
def health():
    expert_status = 'running' if expert_selector is not None else 'error'
    
    return jsonify({
        'status': 'healthy',
        'services': {
            'api': 'running',
            'telegram_bot': telegram_status,
            'expert_system': expert_status
        }
    })

@app.route('/ask', methods=['POST'])
async def ask():
    try:
        if expert_selector is None:
            return jsonify({
                'status': 'error',
                'error': 'Expert system is not initialized',
                'code': 'EXPERT_SYSTEM_ERROR'
            }), 500

        data = request.get_json()
        question = data.get('question')
        
        if not question:
            return jsonify({
                'status': 'error',
                'error': 'Question is required',
                'code': 'MISSING_QUESTION'
            }), 400

        # Select expert and get response
        expert_type, direct_response = await expert_selector.select_expert(question)
        
        if expert_type:
            if expert_type == "sports" and sports_expert:
                response = await sports_expert.get_response(question)
            elif expert_type == "food" and food_expert:
                response = await food_expert.get_response(question)
            elif expert_type == "ai" and ai_expert:
                response = await ai_expert.get_response(question)
            elif expert_type == "sudostar" and sudostar_expert:
                response = await sudostar_expert.get_response(question)
            else:
                response = None
        else:
            response = direct_response

        if not response:
            return jsonify({
                'status': 'error',
                'error': 'Could not generate response',
                'code': 'NO_RESPONSE'
            }), 500

        return jsonify({
            'status': 'success',
            'data': {
                'answer': response,
                'expert_type': expert_type or 'general'
            }
        })

    except Exception as e:
        print(f"Error in /ask endpoint: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'code': 'INTERNAL_ERROR'
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 