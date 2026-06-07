import os
import json
import uuid
import hashlib
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, redirect, session, url_for, send_file
from werkzeug.utils import secure_filename
import requests
from urllib.parse import urlencode
from io import BytesIO
import base64
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')

# Gmail OAuth
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/callback')

# File upload config
UPLOAD_FOLDER = 'uploads'
MUSIC_FOLDER = 'music'
ALLOWED_IMAGE_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_MUSIC_EXT = {'mp3', 'wav', 'm4a', 'ogg'}
MAX_FILE_SIZE = 10 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MUSIC_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MUSIC_FOLDER'] = MUSIC_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Database
DB_URL = os.environ.get('DATABASE_URL')
DATA_DIR = 'data'
TEMPLATES_FILE = os.path.join(DATA_DIR, 'templates.json')
ADS_CONFIG_FILE = 'ads_config.json'
os.makedirs(DATA_DIR, exist_ok=True)

# ========== DATABASE CONNECTION ==========
def get_db_connection():
    try:
        import psycopg2
        conn = psycopg2.connect(DB_URL)
        return conn
    except Exception as e:
        print(f"❌ Database error: {e}")
        return None

# ========== INIT DATABASE ==========
def init_db():
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            
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
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT,
                    picture_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS reviews (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    product_id TEXT NOT NULL,
                    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                    review_text TEXT,
                    verified_purchase BOOLEAN DEFAULT false,
                    helpful_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS product_queries (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    product_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    screenshot_url TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS query_responses (
                    id SERIAL PRIMARY KEY,
                    query_id INTEGER REFERENCES product_queries(id),
                    admin_response TEXT NOT NULL,
                    responded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS wishlist (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    product_id TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS cart (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    product_id TEXT NOT NULL,
                    quantity INTEGER DEFAULT 1,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP
                )
            ''')
            
            conn.commit()
            cur.close()
            conn.close()
            print("✅ Database tables initialized!")
    except Exception as e:
        print(f"❌ DB init error: {e}")

init_db()

# ========== HELPER FUNCTIONS ==========
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

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Login required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin' not in session:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def get_user_from_db(email):
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('SELECT id, email, name, picture_url FROM users WHERE email = %s', (email,))
            user = cur.fetchone()
            cur.close()
            conn.close()
            if user:
                return {'id': user[0], 'email': user[1], 'name': user[2], 'picture_url': user[3]}
    except:
        pass
    return None

def create_user_in_db(email, name, picture_url):
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO users (email, name, picture_url, created_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id, email, name
            ''', (email, name, picture_url, datetime.now()))
            user = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            if user:
                return {'id': user[0], 'email': user[1], 'name': user[2], 'picture_url': picture_url}
    except Exception as e:
        print(f"Error creating user: {e}")
    return None

# ========== ADMIN LOGIN ==========
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'GET':
        try:
            with open('templates/login.html', 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return '<h1>Login page not found</h1>', 404
    
    password = request.form.get('password')
    if not password:
        return redirect('/admin-login?error=No password provided')
    
    if password == ADMIN_PASSWORD:
        session['admin'] = True
        return redirect('/admin')
    else:
        return redirect('/admin-login?error=Wrong password')

@app.route('/admin-logout')
def admin_logout():
    session.clear()
    return redirect('/')

# ========== GMAIL OAUTH ROUTES ==========
@app.route('/auth/gmail', methods=['POST'])
def gmail_login():
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': GOOGLE_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'openid email profile'
    }
    auth_url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode(params)
    return jsonify({'auth_url': auth_url})

@app.route('/auth/callback')
def gmail_callback():
    code = request.args.get('code')
    if not code:
        return redirect('/?error=no_code')
    
    try:
        token_data = {
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': GOOGLE_REDIRECT_URI
        }
        
        response = requests.post('https://oauth2.googleapis.com/token', data=token_data)
        tokens = response.json()
        
        if 'access_token' not in tokens:
            return redirect('/?error=token_failed')
        
        headers = {'Authorization': f"Bearer {tokens['access_token']}"}
        user_response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers=headers
        )
        user_info = user_response.json()
        
        user = get_user_from_db(user_info['email'])
        if not user:
            user = create_user_in_db(
                user_info['email'],
                user_info.get('name', 'User'),
                user_info.get('picture', '')
            )
        
        if user:
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_name'] = user['name']
            return redirect('/')
        
        return redirect('/?error=user_creation_failed')
    
    except Exception as e:
        print(f"Gmail callback error: {e}")
        return redirect('/?error=callback_error')

@app.route('/auth/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/api/user/profile')
@login_required
def get_user_profile():
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('''
                SELECT id, email, name, picture_url, created_at
                FROM users WHERE id = %s
            ''', (session['user_id'],))
            user = cur.fetchone()
            cur.close()
            conn.close()
            if user:
                return jsonify({
                    'id': user[0],
                    'email': user[1],
                    'name': user[2],
                    'picture_url': user[3],
                    'created_at': user[4].isoformat() if user[4] else None
                })
    except:
        pass
    return jsonify({'error': 'User not found'}), 404

# ========== PRODUCT MANAGEMENT ==========
@app.route('/api/products', methods=['GET'])
def get_all_products():
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM products WHERE active = true ORDER BY created_at DESC')
            rows = cur.fetchall()
            cur.close()
            conn.close()
            
            products = []
            for row in rows:
                images = row[7] if row[7] else []
                products.append({
                    'id': row[1],
                    'name': row[2],
                    'price': row[3],
                    'original_price': row[4],
                    'category': row[5],
                    'description': row[6],
                    'images': images,
                    'affiliate_link': row[8],
                    'active': row[9],
                    'created_at': row[10].isoformat() if row[10] else None
                })
            return jsonify(products)
    except Exception as e:
        print(f"Error fetching products: {e}")
    
    return jsonify([])

@app.route('/api/products/<product_id>', methods=['GET'])
def get_single_product(product_id):
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM products WHERE product_id = %s', (product_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                return jsonify({
                    'id': row[1],
                    'name': row[2],
                    'price': row[3],
                    'original_price': row[4],
                    'category': row[5],
                    'description': row[6],
                    'images': row[7] if row[7] else [],
                    'affiliate_link': row[8],
                    'active': row[9]
                }), 200
    except Exception as e:
        print(f"Error: {e}")
    
    return jsonify({'error': 'Product not found'}), 404

@app.route('/api/products', methods=['POST'])
def add_product():
    try:
        name = request.form.get('name')
        price = request.form.get('price')
        affiliate_link = request.form.get('affiliate_link')
        category = request.form.get('category', 'other')
        description = request.form.get('description', '')
        original_price = request.form.get('original_price', '')
        
        if not name or not price or not affiliate_link:
            return jsonify({'error': 'Missing required fields'}), 400
        
        product_id = str(uuid.uuid4())
        images = []
        
        # Handle image URLs
        image_urls = request.form.get('image_urls', '').strip()
        if image_urls:
            url_list = [url.strip() for url in image_urls.split(',') if url.strip()]
            images.extend(url_list)
        
        # Handle file uploads
        if 'productImages' in request.files:
            files = request.files.getlist('productImages')
            
            if len(images) + len(files) > 5:
                return jsonify({'error': 'Maximum 5 total images'}), 400
            
            for file in files:
                if file and file.filename and allowed_image(file.filename):
                    try:
                        filename = secure_filename(file.filename)
                        filename = f"{uuid.uuid4()}_{filename}"
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(filepath)
                        images.append(f'/uploads/{filename}')
                    except Exception as e:
                        print(f"Error uploading image: {e}")
                        continue
        
        if not images:
            return jsonify({'error': 'At least one image is required'}), 400
        
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO products 
                (product_id, name, price, original_price, category, description, images, affiliate_link, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING product_id, name, price, original_price, category, description, images, affiliate_link
            ''', (
                product_id, name, price, original_price, category, description,
                images, affiliate_link, datetime.now()
            ))
            product = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            
            if product:
                return jsonify({
                    'message': 'Product added successfully!',
                    'product': {
                        'id': product[0],
                        'name': product[1],
                        'price': product[2],
                        'original_price': product[3],
                        'category': product[4],
                        'description': product[5],
                        'images': product[6],
                        'affiliate_link': product[7]
                    }
                }), 201
    
    except Exception as e:
        print(f"Error adding product: {e}")
    
    return jsonify({'error': 'Failed to add product'}), 500

@app.route('/api/products/<product_id>', methods=['PUT'])
def update_product(product_id):
    try:
        name = request.form.get('name')
        price = request.form.get('price')
        affiliate_link = request.form.get('affiliate_link')
        category = request.form.get('category', 'other')
        description = request.form.get('description', '')
        original_price = request.form.get('original_price', '')
        
        if not name or not price or not affiliate_link:
            return jsonify({'error': 'Missing required fields'}), 400
        
        images = []
        
        # Handle image URLs
        image_urls = request.form.get('image_urls', '').strip()
        if image_urls:
            url_list = [url.strip() for url in image_urls.split(',') if url.strip()]
            images.extend(url_list)
        
        # Handle file uploads
        if 'productImages' in request.files:
            files = request.files.getlist('productImages')
            
            if len(images) + len(files) > 5:
                return jsonify({'error': 'Maximum 5 total images'}), 400
            
            for file in files:
                if file and file.filename and allowed_image(file.filename):
                    try:
                        filename = secure_filename(file.filename)
                        filename = f"{uuid.uuid4()}_{filename}"
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(filepath)
                        images.append(f'/uploads/{filename}')
                    except Exception as e:
                        print(f"Error uploading image: {e}")
                        continue
        
        # If no new images provided, keep old ones
        if not images:
            conn = get_db_connection()
            if conn:
                cur = conn.cursor()
                cur.execute('SELECT images FROM products WHERE product_id = %s', (product_id,))
                row = cur.fetchone()
                cur.close()
                conn.close()
                if row and row[0]:
                    images = row[0]
        
        # Update in database
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('''
                UPDATE products 
                SET name = %s, price = %s, original_price = %s,
                    category = %s, description = %s, images = %s,
                    affiliate_link = %s, updated_at = %s
                WHERE product_id = %s
                RETURNING product_id, name, price, original_price, category, description, images, affiliate_link
            ''', (
                name, price, original_price, category, description,
                images, affiliate_link, datetime.now(), product_id
            ))
            product = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            
            if product:
                return jsonify({
                    'message': 'Product updated!',
                    'product': {
                        'id': product[0],
                        'name': product[1],
                        'price': product[2],
                        'original_price': product[3],
                        'category': product[4],
                        'description': product[5],
                        'images': product[6],
                        'affiliate_link': product[7]
                    }
                }), 200
    
    except Exception as e:
        print(f"Error updating product: {e}")
    
    return jsonify({'error': 'Failed to update product'}), 500

@app.route('/uploads/<filename>')
def serve_image(filename):
    try:
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(filepath):
            return send_file(filepath, mimetype='image/*')
    except Exception as e:
        print(f"Error serving image: {e}")
    return jsonify({'error': 'Image not found'}), 404

# ========== ROUTES ==========
@app.route('/')
def index():
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return '<h1>index.html not found</h1>', 404

@app.route('/admin')
def admin():
    if 'admin' not in session:
        return redirect('/admin-login')
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return '<h1>Admin dashboard not found</h1>', 404

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
