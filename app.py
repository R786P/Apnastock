import os
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, redirect, session, send_from_directory
from werkzeug.utils import secure_filename

# Load .env for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'super-secret-key-change-in-prod')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'ApnaStock@2026')

# Config
UPLOAD_FOLDER = 'uploads'
MUSIC_FOLDER = 'music'
DATA_DIR = 'data'
ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_MUSIC_EXT = {'mp3', 'wav', 'm4a', 'ogg'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MUSIC_FOLDER, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MUSIC_FOLDER'] = MUSIC_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# JSON File Paths
PRODUCTS_FILE = os.path.join(DATA_DIR, 'products.json')
ADS_FILE = os.path.join(DATA_DIR, 'ads_config.json')
TEMPLATES_FILE = os.path.join(DATA_DIR, 'templates.json')
ORDERS_FILE = os.path.join(DATA_DIR, 'orders.json')

def init_files():
    defaults = {
        PRODUCTS_FILE: [],
        ADS_FILE: {'google_adsense_enabled': False, 'google_publisher_id': '', 'sponsor_ads': []},
        TEMPLATES_FILE: [],
        ORDERS_FILE: []
    }
    for path, default in defaults.items():
        if not os.path.exists(path):
            with open(path, 'w') as f:
                json.dump(default, f)

init_files()

# Helpers
def allowed_file(filename, allowed_ext):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_ext

def read_json(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return [] if any(k in path for k in ['products', 'orders', 'templates']) else {}

def write_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

# ========== CORE ROUTES ==========
@app.route('/')
def index():
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return '<h1>index.html not found</h1>', 404

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect('/')
    return redirect('/')  # Frontend JS will show admin panel based on session

@app.route('/admin-login', methods=['POST'])
def login():
    # Support both form-data and JSON
    pwd = request.form.get('password') or (request.json.get('password') if request.is_json else None)
    if pwd == ADMIN_PASSWORD:
        session['logged_in'] = True
        session.permanent = True
        return jsonify({'success': True, 'message': 'Login successful'}), 200
    return jsonify({'error': 'Wrong password'}), 401

@app.route('/admin-logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/api/auth/status')
def auth_status():
    return jsonify({'logged_in': session.get('logged_in', False)})

# ========== PRODUCTS ==========
@app.route('/api/products', methods=['GET'])
def get_all_products():
    cat = request.args.get('category', 'all')
    prods = read_json(PRODUCTS_FILE)
    if cat != 'all':
        prods = [p for p in prods if p.get('category') == cat]
    prods.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return jsonify(prods)

@app.route('/api/products', methods=['POST'])
def add_product():
    name = request.form.get('name')
    price = request.form.get('price')
    affiliate_link = request.form.get('affiliate_link')
    category = request.form.get('category', 'other')
    description = request.form.get('description', '')
    original_price = request.form.get('original_price', '')
    
    if not name or not price or not affiliate_link:
        return jsonify({'error': 'Missing required fields'}), 400
    
    images = []
    if 'images' in request.files:
        files = request.files.getlist('images')
        if len(files) > 5:
            return jsonify({'error': 'Maximum 5 images allowed'}), 400
        
        for file in files:
            if file and file.filename and allowed_file(file.filename, ALLOWED_IMAGE_EXT):
                filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                images.append(f'/uploads/{filename}')
            elif file and file.filename:
                return jsonify({'error': f'Invalid image type: {file.filename}'}), 400
    
    if not images:
        return jsonify({'error': 'At least one image required'}), 400
    
    prod = {
        'id': str(uuid.uuid4()), 'name': name, 'price': price,
        'original_price': original_price, 'images': images,
        'affiliate_link': affiliate_link, 'category': category,
        'description': description, 'active': True,
        'created_at': datetime.now().isoformat()
    }
    
    prods = read_json(PRODUCTS_FILE)
    prods.append(prod)
    write_json(PRODUCTS_FILE, prods)
    return jsonify({'message': 'Added', 'product': prod}), 201

@app.route('/api/products/<pid>', methods=['PUT'])
def edit_product(pid):
    prods = read_json(PRODUCTS_FILE)
    prod = next((p for p in prods if p['id'] == pid), None)
    if not prod:
        return jsonify({'error': 'Not found'}), 404
    
    prod['name'] = request.form.get('name') or prod['name']
    prod['price'] = request.form.get('price') or prod['price']
    prod['affiliate_link'] = request.form.get('affiliate_link') or prod['affiliate_link']
    prod['category'] = request.form.get('category', prod['category'])
    prod['description'] = request.form.get('description', prod['description'])
    prod['original_price'] = request.form.get('original_price', prod['original_price'])
    
    if 'images' in request.files:
        files = request.files.getlist('images')
        new_images = []
        for file in files:
            if file and file.filename and allowed_file(file.filename, ALLOWED_IMAGE_EXT):
                filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                new_images.append(f'/uploads/{filename}')
        if new_images:
            prod['images'] = new_images
    
    prod['updated_at'] = datetime.now().isoformat()
    write_json(PRODUCTS_FILE, prods)
    return jsonify({'message': 'Updated', 'product': prod}), 200

@app.route('/api/products/<pid>', methods=['DELETE'])
def del_product(pid):
    prods = read_json(PRODUCTS_FILE)
    prod = next((p for p in prods if p['id'] == pid), None)
    if prod:
        for img in prod.get('images', []):
            if img.startswith('/uploads/'):
                try: os.remove(os.path.join(UPLOAD_FOLDER, img.split('/')[-1]))
                except: pass
    write_json(PRODUCTS_FILE, [p for p in prods if p['id'] != pid])
    return jsonify({'message': 'Deleted'}), 200

# ========== TEMPLATES ==========
@app.route('/api/templates', methods=['GET'])
def get_all_templates():
    return jsonify(read_json(TEMPLATES_FILE))

@app.route('/api/templates', methods=['POST'])
def add_template():
    data = request.get_json()
    if not data or 'name' not in data or 'colors' not in data:
        return jsonify({'error': 'Missing fields'}), 400
    template = {'id': str(uuid.uuid4()), 'name': data['name'], 'colors': data['colors'], 'fonts': data.get('fonts', {}), 'layout': data.get('layout', 'grid'), 'created_at': datetime.now().isoformat()}
    templates = read_json(TEMPLATES_FILE)
    templates.append(template)
    write_json(TEMPLATES_FILE, templates)
    return jsonify({'message': 'Added', 'template': template}), 201

@app.route('/api/templates/<tid>', methods=['DELETE'])
def del_template(tid):
    templates = read_json(TEMPLATES_FILE)
    write_json(TEMPLATES_FILE, [t for t in templates if t['id'] != tid])
    return jsonify({'message': 'Deleted'}), 200

# ========== MUSIC ==========
@app.route('/api/music', methods=['POST'])
def upload_music():
    if 'music' not in request.files:
        return jsonify({'error': 'No music file'}), 400
    file = request.files['music']
    if not file or not file.filename or not allowed_file(file.filename, ALLOWED_MUSIC_EXT):
        return jsonify({'error': 'Invalid music file'}), 400
    filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
    file.save(os.path.join(app.config['MUSIC_FOLDER'], filename))
    return jsonify({'message': 'Uploaded', 'file': f'/music/{filename}'}), 201

@app.route('/api/music', methods=['GET'])
def get_music_files():
    files = []
    try:
        for f in os.listdir(app.config['MUSIC_FOLDER']):
            if allowed_file(f, ALLOWED_MUSIC_EXT):
                files.append({'name': f, 'url': f'/music/{f}'})
    except: pass
    return jsonify(files)

# ========== ADS ==========
@app.route('/api/ads/config', methods=['GET'])
def get_ads_cfg():
    return jsonify(read_json(ADS_FILE))

@app.route('/api/ads/config', methods=['POST'])
def update_ads_cfg():
    data = request.get_json()
    cfg = read_json(ADS_FILE)
    if 'google_adsense_enabled' in data: cfg['google_adsense_enabled'] = data['google_adsense_enabled']
    if 'google_publisher_id' in data: cfg['google_publisher_id'] = data['google_publisher_id']
    write_json(ADS_FILE, cfg)
    return jsonify({'message': 'Updated', 'config': cfg})

@app.route('/api/ads/sponsor', methods=['POST'])
def add_sponsor():
    data = request.get_json()
    if not data or not all(k in data for k in ['company_name', 'image_url', 'ad_link']):
        return jsonify({'error': 'Missing'}), 400
    cfg = read_json(ADS_FILE)
    sponsor = {'id': str(uuid.uuid4()), 'company_name': data['company_name'], 'image_url': data['image_url'], 'ad_link': data['ad_link'], 'position': data.get('position', 'banner_top'), 'active': True, 'created_at': datetime.now().isoformat()}
    cfg['sponsor_ads'].append(sponsor)
    write_json(ADS_FILE, cfg)
    return jsonify({'message': 'Added', 'sponsor': sponsor}), 201

@app.route('/api/ads/sponsor/<sid>', methods=['DELETE'])
def del_sponsor(sid):
    cfg = read_json(ADS_FILE)
    cfg['sponsor_ads'] = [s for s in cfg['sponsor_ads'] if s['id'] != sid]
    write_json(ADS_FILE, cfg)
    return jsonify({'message': 'Deleted'})

# ========== ORDERS ==========
@app.route('/api/orders', methods=['GET'])
def get_all_orders():
    orders = read_json(ORDERS_FILE)
    orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return jsonify(orders)

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    if not data or not all(k in data for k in ['customer_name', 'product_id', 'quantity']):
        return jsonify({'error': 'Missing fields'}), 400
    
    products = read_json(PRODUCTS_FILE)
    product = next((p for p in products if p['id'] == data.get('product_id')), None)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    order = {
        'id': f"ORD{str(uuid.uuid4())[:8].upper()}",
        'order_number': len(read_json(ORDERS_FILE)) + 1,
        'customer_name': data.get('customer_name'),
        'customer_email': data.get('customer_email', ''),
        'customer_phone': data.get('customer_phone', ''),
        'product_id': data.get('product_id'),
        'product_name': product['name'],
        'product_price': product['price'],
        'quantity': data.get('quantity'),
        'total_price': float(product['price'].replace('₹', '').strip()) * int(data.get('quantity', 1)),
        'status': 'pending',
        'shipping_address': data.get('shipping_address', ''),
        'tracking_number': f"TRK{str(uuid.uuid4())[:12].upper()}",
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }
    orders = read_json(ORDERS_FILE)
    orders.append(order)
    write_json(ORDERS_FILE, orders)
    return jsonify({'message': 'Order created', 'order': order}), 201

@app.route('/api/orders/<order_id>', methods=['PUT'])
def update_order_status(order_id):
    data = request.get_json()
    if 'status' not in data:
        return jsonify({'error': 'Status required'}), 400
    valid_statuses = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']
    if data['status'] not in valid_statuses:
        return jsonify({'error': 'Invalid status'}), 400
    orders = read_json(ORDERS_FILE)
    order = next((o for o in orders if o['id'] == order_id), None)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    order['status'] = data['status']
    order['updated_at'] = datetime.now().isoformat()
    if 'notes' in data: order['notes'] = data['notes']
    write_json(ORDERS_FILE, orders)
    return jsonify({'message': 'Order updated', 'order': order})

@app.route('/api/orders/track/<tracking_number>', methods=['GET'])
def track_order(tracking_number):
    orders = read_json(ORDERS_FILE)
    order = next((o for o in orders if o.get('tracking_number') == tracking_number), None)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    return jsonify(order)

@app.route('/api/orders/<order_id>', methods=['DELETE'])
def delete_order(order_id):
    orders = read_json(ORDERS_FILE)
    write_json(ORDERS_FILE, [o for o in orders if o['id'] != order_id])
    return jsonify({'message': 'Deleted'})

# ========== STATIC FILE SERVING ==========
@app.route('/uploads/<filename>')
def serve_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/music/<filename>')
def serve_music(filename):
    return send_from_directory(MUSIC_FOLDER, filename)

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
