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

# ✅ SECURE - Only from environment variables, NO defaults!
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')

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

# Database Connection
DB_URL = os.environ.get('DATABASE_URL')

# For backward compatibility - still keep JSON for non-database data
DATA_DIR = 'data'
TEMPLATES_FILE = os.path.join(DATA_DIR, 'templates.json')
ADS_CONFIG_FILE = 'ads_config.json'

os.makedirs(DATA_DIR, exist_ok=True)

# Database Connection Function
def get_db_connection():
    try:
        import psycopg2
        conn = psycopg2.connect(DB_URL)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# Initialize database tables if they don't exist
def init_db():
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            
            # Create products table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    product_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    price TEXT NOT NULL,
                    original_price TEXT,
                    category TEXT,
                    description TEXT,
                    images TEXT[],
                    affiliate_link TEXT,
                    active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP
                )
            ''')
            
            # Create orders table
            cur.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    order_id TEXT UNIQUE NOT NULL,
                    order_number INTEGER,
                    customer_name TEXT NOT NULL,
                    customer_email TEXT,
                    customer_phone TEXT,
                    product_id TEXT NOT NULL,
                    product_name TEXT,
                    product_price TEXT,
                    quantity INTEGER,
                    total_price FLOAT,
                    status TEXT DEFAULT 'pending',
                    shipping_address TEXT,
                    tracking_number TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP
                )
            ''')
            
            conn.commit()
            cur.close()
            conn.close()
            print("✅ Database tables initialized!")
    except Exception as e:
        print(f"Database init error: {e}")

init_db()

def init_files():
    if not os.path.exists(TEMPLATES_FILE):
        with open(TEMPLATES_FILE, 'w') as f:
            json.dump([], f)
    if not os.path.exists(ADS_CONFIG_FILE):
        with open(ADS_CONFIG_FILE, 'w') as f:
            json.dump({
                'google_adsense': {
                    'enabled': False,
                    'publisher_id': ''
                },
                'sponsor_ads': []
            }, f, indent=2)

init_files()

def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXT

def allowed_music(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_MUSIC_EXT

# Database Functions
def get_products():
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM products ORDER BY created_at DESC')
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            products = []
            for row in rows:
                products.append({
                    'id': row[1],
                    'name': row[2],
                    'price': row[3],
                    'original_price': row[4],
                    'category': row[5],
                    'description': row[6],
                    'images': row[7] if row[7] else [],
                    'affiliate_link': row[8],
                    'active': row[9],
                    'created_at': row[10].isoformat() if row[10] else None,
                    'updated_at': row[11].isoformat() if row[11] else None
                })
            return products
        return []
    except Exception as e:
        print(f"Error getting products: {e}")
        return []

def save_product(prod):
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO products 
                (product_id, name, price, original_price, category, description, images, affiliate_link, active, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                prod['id'],
                prod['name'],
                prod['price'],
                prod.get('original_price', ''),
                prod.get('category', 'other'),
                prod.get('description', ''),
                prod.get('images', []),
                prod['affiliate_link'],
                prod.get('active', True),
                prod.get('created_at', datetime.now())
            ))
            conn.commit()
            cur.close()
            conn.close()
            return True
    except Exception as e:
        print(f"Error saving product: {e}")
        return False

def update_product_db(pid, prod):
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('''
                UPDATE products
                SET name=%s, price=%s, original_price=%s, category=%s, 
                    description=%s, images=%s, affiliate_link=%s, updated_at=%s
                WHERE product_id=%s
            ''', (
                prod['name'],
                prod['price'],
                prod.get('original_price', ''),
                prod.get('category', 'other'),
                prod.get('description', ''),
                prod.get('images', []),
                prod['affiliate_link'],
                datetime.now(),
                pid
            ))
            conn.commit()
            cur.close()
            conn.close()
            return True
    except Exception as e:
        print(f"Error updating product: {e}")
        return False

def delete_product_db(pid):
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('DELETE FROM products WHERE product_id=%s', (pid,))
            conn.commit()
            cur.close()
            conn.close()
            return True
    except Exception as e:
        print(f"Error deleting product: {e}")
        return False

def get_ads():
    try:
        with open(ADS_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return {
            'google_adsense': {
                'enabled': False,
                'publisher_id': ''
            },
            'sponsor_ads': []
        }

def save_ads(a):
    with open(ADS_CONFIG_FILE, 'w') as f:
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
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM orders ORDER BY created_at DESC')
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            orders = []
            for row in rows:
                orders.append({
                    'id': row[1],
                    'order_number': row[2],
                    'customer_name': row[3],
                    'customer_email': row[4],
                    'customer_phone': row[5],
                    'product_id': row[6],
                    'product_name': row[7],
                    'product_price': row[8],
                    'quantity': row[9],
                    'total_price': row[10],
                    'status': row[11],
                    'shipping_address': row[12],
                    'tracking_number': row[13],
                    'notes': row[14] if len(row) > 14 else '',
                    'created_at': row[15].isoformat() if len(row) > 15 and row[15] else None,
                    'updated_at': row[16].isoformat() if len(row) > 16 and row[16] else None
                })
            return orders
        return []
    except Exception as e:
        print(f"Error getting orders: {e}")
        return []

def save_order(order):
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO orders
                (order_id, order_number, customer_name, customer_email, customer_phone,
                 product_id, product_name, product_price, quantity, total_price, status,
                 shipping_address, tracking_number, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                order['id'],
                order['order_number'],
                order['customer_name'],
                order.get('customer_email', ''),
                order.get('customer_phone', ''),
                order['product_id'],
                order['product_name'],
                order['product_price'],
                order['quantity'],
                order['total_price'],
                order.get('status', 'pending'),
                order.get('shipping_address', ''),
                order.get('tracking_number', ''),
                order.get('created_at', datetime.now())
            ))
            conn.commit()
            cur.close()
            conn.close()
            return True
    except Exception as e:
        print(f"Error saving order: {e}")
        return False

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
    
    if save_product(prod):
        return jsonify({'message': 'Added', 'product': prod}), 201
    return jsonify({'error': 'Failed to save product'}), 500

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
    
    if update_product_db(pid, prod):
        return jsonify({'message': 'Updated', 'product': prod}), 200
    return jsonify({'error': 'Failed to update'}), 500

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
    
    if delete_product_db(pid):
        return jsonify({'message': 'Deleted'}), 200
    return jsonify({'error': 'Failed to delete'}), 500

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
    
    if 'google_adsense' in data:
        if 'enabled' in data['google_adsense']:
            cfg['google_adsense']['enabled'] = data['google_adsense']['enabled']
        if 'publisher_id' in data['google_adsense']:
            cfg['google_adsense']['publisher_id'] = data['google_adsense']['publisher_id']
    
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
    
    if save_order(order):
        return jsonify({'message': 'Order created', 'order': order}), 201
    return jsonify({'error': 'Failed to create order'}), 500

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
    
    # Update in database
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('''
                UPDATE orders SET status=%s, updated_at=%s WHERE order_id=%s
            ''', (order['status'], order['updated_at'], order_id))
            conn.commit()
            cur.close()
            conn.close()
    except:
        pass
    
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
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('DELETE FROM orders WHERE order_id=%s', (order_id,))
            conn.commit()
            cur.close()
            conn.close()
    except:
        pass
    
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
