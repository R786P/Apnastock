import os
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, redirect, session

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

app = Flask(__name__)

app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'secret-2026')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'ApnaStock@2026')

DATA_DIR = 'data'
PRODUCTS_FILE = os.path.join(DATA_DIR, 'products.json')
ADS_FILE = os.path.join(DATA_DIR, 'ads_config.json')

os.makedirs(DATA_DIR, exist_ok=True)

def init_files():
    if not os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, 'w') as f:
            json.dump([], f)
    if not os.path.exists(ADS_FILE):
        with open(ADS_FILE, 'w') as f:
            json.dump({'google_adsense_enabled': False, 'google_publisher_id': '', 'sponsor_ads': []}, f)

init_files()

def get_products():
    try:
        with open(PRODUCTS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_products(p):
    with open(PRODUCTS_FILE, 'w') as f:
        json.dump(p, f, indent=2)

def get_ads():
    try:
        with open(ADS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {'google_adsense_enabled': False, 'google_publisher_id': '', 'sponsor_ads': []}

def save_ads(a):
    with open(ADS_FILE, 'w') as f:
        json.dump(a, f, indent=2)

@app.route('/')
def index():
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return '<h1>index.html not found</h1>', 404

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect('/')
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return '<h1>index.html not found</h1>', 404

@app.route('/admin-login', methods=['POST'])
def login():
    pwd = request.form.get('password')
    if pwd == ADMIN_PASSWORD:
        session['logged_in'] = True
        try:
            with open('index.html', 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return '<h1>index.html not found</h1>', 404
    return jsonify({'error': 'Wrong'}), 401

@app.route('/admin-logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/api/products', methods=['GET'])
def get_all_products():
    cat = request.args.get('category', 'all')
    prods = get_products()
    if cat != 'all':
        prods = [p for p in prods if p.get('category') == cat]
    prods.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return jsonify(prods)

@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.get_json()
    if not data or not all(k in data for k in ['name', 'price', 'affiliate_link', 'images']):
        return jsonify({'error': 'Missing fields'}), 400
    
    prod = {
        'id': str(uuid.uuid4()),
        'name': data.get('name'),
        'price': data.get('price'),
        'original_price': data.get('original_price', ''),
        'images': data.get('images') if isinstance(data.get('images'), list) else [data.get('images')],
        'affiliate_link': data.get('affiliate_link'),
        'category': data.get('category', 'other'),
        'description': data.get('description', ''),
        'active': True,
        'created_at': datetime.now().isoformat()
    }
    
    prods = get_products()
    prods.append(prod)
    save_products(prods)
    return jsonify({'message': 'Added', 'product': prod}), 201

@app.route('/api/products/<pid>', methods=['DELETE'])
def del_product(pid):
    prods = get_products()
    prods = [p for p in prods if p['id'] != pid]
    save_products(prods)
    return jsonify({'message': 'Deleted'})

@app.route('/api/ads/config', methods=['GET'])
def get_ads_cfg():
    return jsonify(get_ads())

@app.route('/api/ads/config', methods=['POST'])
def update_ads_cfg():
    data = request.get_json()
    cfg = get_ads()
    if 'google_adsense_enabled' in data:
        cfg['google_adsense_enabled'] = data['google_adsense_enabled']
    if 'google_publisher_id' in data:
        cfg['google_publisher_id'] = data['google_publisher_id']
    save_ads(cfg)
    return jsonify({'message': 'Updated', 'config': cfg})

@app.route('/api/ads/sponsor', methods=['POST'])
def add_sponsor():
    data = request.get_json()
    if not data or not all(k in data for k in ['company_name', 'image_url', 'ad_link']):
        return jsonify({'error': 'Missing'}), 400
    
    cfg = get_ads()
    sponsor = {
        'id': str(uuid.uuid4()),
        'company_name': data.get('company_name'),
        'image_url': data.get('image_url'),
        'ad_link': data.get('ad_link'),
        'position': data.get('position', 'banner_top'),
        'active': True,
        'created_at': datetime.now().isoformat()
    }
    cfg['sponsor_ads'].append(sponsor)
    save_ads(cfg)
    return jsonify({'message': 'Added', 'sponsor': sponsor}), 201

@app.route('/api/ads/sponsor/<sid>', methods=['DELETE'])
def del_sponsor(sid):
    cfg = get_ads()
    cfg['sponsor_ads'] = [s for s in cfg['sponsor_ads'] if s['id'] != sid]
    save_ads(cfg)
    return jsonify({'message': 'Deleted'})

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
