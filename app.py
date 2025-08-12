import os
import json
import re
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import requests

load_dotenv()
app = Flask(__name__)

# Load static recipes once at startup
with open('recipes.json', 'r', encoding='utf-8') as f:
    RECIPES = json.load(f)

def normalize(s: str) -> str:
    return re.sub(r'\s+', ' ', s.strip().lower())

def parse_ingredients(text: str):
    parts = re.split(r'[,\n;|]+', text)
    return [normalize(p) for p in parts if normalize(p)]

def score_recipe(user_set: set, recipe_ings: list):
    recipe_set = set(normalize(i) for i in recipe_ings)
    matched = sorted(list(user_set & recipe_set))
    missing = sorted(list(recipe_set - user_set))
    match_count = len(matched)
    total = max(len(recipe_set), 1)
    ratio = match_count / total
    return {
        'matched': matched,
        'missing': missing,
        'match_count': match_count,
        'total': total,
        'ratio': ratio
    }

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    ingredients_text = request.form.get('ingredients', '')
    threshold = float(request.form.get('threshold', 0.5))
    user_ings = parse_ingredients(ingredients_text)
    user_set = set(user_ings)

    results = []
    for r in RECIPES:
        sc = score_recipe(user_set, r.get('ingredients', []))
        if sc['ratio'] >= threshold:
            merged = {**r, **sc}   # recipe fields + score fields
            results.append(merged)

    # sort by match ratio desc
    results.sort(key=lambda x: x['ratio'], reverse=True)
    return render_template('results.html', results=results, user_ingredients=user_ings, threshold=threshold)

# Optional: proxy to Spoonacular (use only if you set SPOONACULAR_API_KEY in .env)
@app.route('/api_search')
def api_search():
    ingredients = request.args.get('ingredients', '')
    if not ingredients:
        return jsonify({'error': 'provide ingredients query param'}), 400

    key = os.getenv('SPOONACULAR_API_KEY')
    if not key:
        return jsonify({'error': 'SPOONACULAR_API_KEY not set in .env'}), 500

    params = {
        'ingredients': ingredients,
        'number': 10,
        'apiKey': key
    }
    try:
        resp = requests.get('https://api.spoonacular.com/recipes/findByIngredients', params=params, timeout=10)
        resp.raise_for_status()
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # run with: python app.py
    app.run(debug=True, port=5000)
