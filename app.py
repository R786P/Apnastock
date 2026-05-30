import os
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, redirect, session
from werkzeug.utils import secure_filename

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

app = Flask(__name__)

app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'secret-2026')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'ApnaStock@2026')

# File upload config
UPLOAD_FOLDER = 'uploads'
MUSIC_FOLDER = 'music'
ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_MUSIC_EXT = {'mp3', 'wav', 'm4a', 'ogg'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MUSIC_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MUSIC_FOLDER'] = MUSIC_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

DATA_DIR = 'data'
PRODUCTS_FILE = os.path.join(DATA_DIR, 'products.json')
ADS_FILE = os.path.join(DATA_DIR, 'ads_config.json')
TEMPLATES_FILE = os.path.join(DATA_DIR, 'templates.json')
ORDERS_FILE = os.path.join(DATA_DIR, 'orders.json')

os.makedirs(DATA_DIR, exist_ok=True)

def init_files():
    if not os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, 'w') as f:
            json.dump([], f)
    if not os.path.exists(ADS_FILE):
        with open(ADS_FILE, 'w') as f:
            json.dump({'google_adsense_enabled': False, 'google_publisher_id': '', 'sponsor_ads': []}, f)
    if not os.path.exists(TEMPLATES_FILE):
        with open(TEMPLATES_FILE, 'w') as f:
            json.dump([], f)
    if not os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, 'w') as f:
            json.dump([], f)

init_files()

def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXT

def allowed_music(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_MUSIC_EXT

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

def get_templates():
    try:
        with open(TEMPLATES_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_templates(t):
    with open(TEMPLATES_FILE, 'w') as f:
        json.dump(t, f, indent=2)

def get_orders():
    try:
        with open(ORDERS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_orders(o):
    with open(ORDERS_FILE, 'w') as f:
        json.dump(o, f, indent=2)

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

# ========== PRODUCTS ==========

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
    name = request.form.get('name')
    price = request.form.get('price')
    affiliate_link = request.form.get('affiliate_link')
    category = request.form.get('category', 'other')
    description = request.form.get('description', '')
    original_price = request.form.get('original_price', '')
    
    if not name or not price or not affiliate_link:
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Handle image uploads
    images = []
    if 'images' in request.files:
        files = request.files.getlist('images')
        
        if len(files) > 5:
            return jsonify({'error': 'Maximum 5 images allowed'}), 400
        
        for file in files:
            if file and file.filename and allowed_image(file.filename):
                filename = secure_filename(file.filename)
                filename = f"{uuid.uuid4()}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                images.append(f'/uploads/{filename}')
            elif file and file.filename:
                return jsonify({'error': f'Invalid image type: {file.filename}'}), 400
    
    if not images:
        return jsonify({'error': 'At least one image required'}), 400
    
    prod = {
        'id': str(uuid.uuid4()),
        'name': name,
        'price': price,
        'original_price': original_price,
        'images': images,
        'affiliate_link': affiliate_link,
        'category': category,
        'description': description,
        'active': True,
        'created_at': datetime.now().isoformat()
    }
    
    prods = get_products()
    prods.append(prod)
    save_products(prods)
    return jsonify({'message': 'Added', 'product': prod}), 201

@app.route('/api/products/<pid>', methods=['GET'])
def get_product(pid):
    prods = get_products()
    prod = next((p for p in prods if p['id'] == pid), None)
    if prod:
        return jsonify(prod)
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/products/<pid>', methods=['PUT'])
def edit_product(pid):
    name = request.form.get('name')
    price = request.form.get('price')
    affiliate_link = request.form.get('affiliate_link')
    category = request.form.get('category', 'other')
    description = request.form.get('description', '')
    original_price = request.form.get('original_price', '')
    
    prods = get_products()
    prod = next((p for p in prods if p['id'] == pid), None)
    
    if not prod:
        return jsonify({'error': 'Not found'}), 404
    
    # Handle new images (optional)
    images = prod.get('images', [])
    if 'images' in request.files:
        files = request.files.getlist('images')
        new_images = []
        
        if len(files) > 5:
            return jsonify({'error': 'Maximum 5 images'}), 400
        
        for file in files:
            if file and file.filename and allowed_image(file.filename):
                filename = secure_filename(file.filename)
                filename = f"{uuid.uuid4()}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                new_images.append(f'/uploads/{filename}')
        
        if new_images:
            images = new_images
    
    prod['name'] = name or prod['name']
    prod['price'] = price or prod['price']
    prod['affiliate_link'] = affiliate_link or prod['affiliate_link']
    prod['category'] = category
    prod['description'] = description
    prod['original_price'] = original_price
    prod['images'] = images
    prod['updated_at'] = datetime.now().isoformat()
    
    save_products(prods)
    return jsonify({'message': 'Updated', 'product': prod}), 200

@app.route('/api/products/<pid>', methods=['DELETE'])
def del_product(pid):
    prods = get_products()
    prod = next((p for p in prods if p['id'] == pid), None)
    if prod:
        for img in prod.get('images', []):
            if img.startswith('/uploads/'):
                try:
                    os.remove(img.replace('/uploads/', UPLOAD_FOLDER + '/'))
                except:
                    pass
    
    prods = [p for p in prods if p['id'] != pid]
    save_products(prods)
    return jsonify({'message': 'Deleted'}), 200

# ========== TEMPLATES ==========

@app.route('/api/templates', methods=['GET'])
def get_all_templates():
    return jsonify(get_templates())

@app.route('/api/templates', methods=['POST'])
def add_template():
    data = request.get_json()
    if not data or 'name' not in data or 'colors' not in data:
        return jsonify({'error': 'Missing fields'}), 400
    
    template = {
        'id': str(uuid.uuid4()),
        'name': data.get('name'),
        'colors': data.get('colors'),
        'fonts': data.get('fonts', {}),
        'layout': data.get('layout', 'grid'),
        'created_at': datetime.now().isoformat()
    }
    
    templates = get_templates()
    templates.append(template)
    save_templates(templates)
    return jsonify({'message': 'Added', 'template': template}), 201

@app.route('/api/templates/<tid>', methods=['DELETE'])
def del_template(tid):
    templates = get_templates()
    templates = [t for t in templates if t['id'] != tid]
    save_templates(templates)
    return jsonify({'message': 'Deleted'}), 200

# ========== MUSIC ==========

@app.route('/api/music', methods=['POST'])
def upload_music():
    if 'music' not in request.files:
        return jsonify({'error': 'No music file'}), 400
    
    file = request.files['music']
    if not file or not file.filename:
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_music(file.filename):
        return jsonify({'error': 'Only mp3, wav, m4a, ogg allowed'}), 400
    
    filename = secure_filename(file.filename)
    filename = f"{uuid.uuid4()}_{filename}"
    filepath = os.path.join(app.config['MUSIC_FOLDER'], filename)
    file.save(filepath)
    
    return jsonify({'message': 'Uploaded', 'file': f'/music/{filename}'}), 201

@app.route('/api/music', methods=['GET'])
def get_music_files():
    files = []
    try:
        for f in os.listdir(app.config['MUSIC_FOLDER']):
            if allowed_music(f):
                files.append({'name': f, 'url': f'/music/{f}'})
    except:
        pass
    return jsonify(files)

# ========== ADS ==========

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

# ========== ORDERS ==========

@app.route('/api/orders', methods=['GET'])
def get_all_orders():
    orders = get_orders()
    orders.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return jsonify(orders)

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    
    if not data or not all(k in data for k in ['customer_name', 'product_id', 'quantity']):
        return jsonify({'error': 'Missing fields'}), 400
    
    # Get product details
    products = get_products()
    product = next((p for p in products if p['id'] == data.get('product_id')), None)
    
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    order = {
        'id': f"ORD{str(uuid.uuid4())[:8].upper()}",
        'order_number': len(get_orders()) + 1,
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
    
    orders = get_orders()
    orders.append(order)
    save_orders(orders)
    
    return jsonify({'message': 'Order created', 'order': order}), 201

@app.route('/api/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    orders = get_orders()
    order = next((o for o in orders if o['id'] == order_id), None)
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    return jsonify(order)

@app.route('/api/orders/<order_id>', methods=['PUT'])
def update_order_status(order_id):
    data = request.get_json()
    
    if 'status' not in data:
        return jsonify({'error': 'Status required'}), 400
    
    valid_statuses = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']
    if data['status'] not in valid_statuses:
        return jsonify({'error': 'Invalid status'}), 400
    
    orders = get_orders()
    order = next((o for o in orders if o['id'] == order_id), None)
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    order['status'] = data['status']
    order['updated_at'] = datetime.now().isoformat()
    
    if 'notes' in data:
        order['notes'] = data['notes']
    
    save_orders(orders)
    
    return jsonify({'message': 'Order updated', 'order': order})

@app.route('/api/orders/track/<tracking_number>', methods=['GET'])
def track_order(tracking_number):
    orders = get_orders()
    order = next((o for o in orders if o.get('tracking_number') == tracking_number), None)
    
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    return jsonify(order)

@app.route('/api/orders/<order_id>', methods=['DELETE'])
def delete_order(order_id):
    orders = get_orders()
    orders = [o for o in orders if o['id'] != order_id]
    save_orders(orders)
    return jsonify({'message': 'Deleted'})

@app.route('/uploads/<filename>')
def serve_image(filename):
    return open(os.path.join(UPLOAD_FOLDER, filename), 'rb'), 200, {'Content-Type': 'image/*'}

@app.route('/music/<filename>')
def serve_music(filename):
    return open(os.path.join(MUSIC_FOLDER, filename), 'rb'), 200, {'Content-Type': 'audio/*'}

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
