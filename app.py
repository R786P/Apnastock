import os
import json
import uuid
import hashlib
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, redirect, session, url_for
from werkzeug.utils import secure_filename
import requests
from urllib.parse import urlencode

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

app = Flask(__name__)

# ✅ SECURE - Only from environment variables
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
            
            # Existing tables
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
            
            # NEW TABLES FOR COMPLETE APP
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

# ========== GMAIL OAUTH ROUTES ==========

@app.route('/auth/gmail', methods=['POST'])
def gmail_login():
    """Initiate Gmail OAuth flow"""
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
    """Handle Gmail OAuth callback"""
    code = request.args.get('code')
    
    if not code:
        return redirect('/?error=no_code')
    
    try:
        # Exchange code for token
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
        
        # Get user info
        headers = {'Authorization': f"Bearer {tokens['access_token']}"}
        user_response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers=headers
        )
        user_info = user_response.json()
        
        # Get or create user
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
    """Get current user profile"""
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

# ========== PRODUCT DETAIL PAGE ==========

@app.route('/api/product/<product_id>')
def get_product_detail(product_id):
    """Get full product details with reviews and queries"""
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            
            # Get product
            cur.execute('SELECT * FROM products WHERE product_id = %s', (product_id,))
            product_row = cur.fetchone()
            
            if not product_row:
                return jsonify({'error': 'Product not found'}), 404
            
            product = {
                'id': product_row[1],
                'name': product_row[2],
                'price': product_row[3],
                'original_price': product_row[4],
                'category': product_row[5],
                'description': product_row[6],
                'images': product_row[7] if product_row[7] else [],
                'affiliate_link': product_row[8],
                'active': product_row[9],
                'created_at': product_row[10].isoformat() if product_row[10] else None
            }
            
            # Get reviews
            cur.execute('''
                SELECT id, user_id, rating, review_text, created_at 
                FROM reviews WHERE product_id = %s 
                ORDER BY created_at DESC LIMIT 10
            ''', (product_id,))
            reviews_rows = cur.fetchall()
            
            reviews = []
            if reviews_rows:
                for rev in reviews_rows:
                    # Get user name
                    cur.execute('SELECT name FROM users WHERE id = %s', (rev[1],))
                    user_name_row = cur.fetchone()
                    reviews.append({
                        'id': rev[0],
                        'user_id': rev[1],
                        'user_name': user_name_row[0] if user_name_row else 'Anonymous',
                        'rating': rev[2],
                        'review_text': rev[3],
                        'created_at': rev[4].isoformat() if rev[4] else None
                    })
            
            # Get queries
            cur.execute('''
                SELECT id, user_id, question, screenshot_url, status, created_at 
                FROM product_queries WHERE product_id = %s 
                ORDER BY created_at DESC LIMIT 10
            ''', (product_id,))
            queries_rows = cur.fetchall()
            
            queries = []
            if queries_rows:
                for q in queries_rows:
                    cur.execute('SELECT name FROM users WHERE id = %s', (q[1],))
                    user_name_row = cur.fetchone()
                    
                    # Get response if exists
                    cur.execute('''
                        SELECT admin_response, responded_at 
                        FROM query_responses WHERE query_id = %s
                    ''', (q[0],))
                    response_row = cur.fetchone()
                    
                    queries.append({
                        'id': q[0],
                        'user_id': q[1],
                        'user_name': user_name_row[0] if user_name_row else 'Anonymous',
                        'question': q[2],
                        'screenshot_url': q[3],
                        'status': q[4],
                        'response': response_row[0] if response_row else None,
                        'response_time': response_row[1].isoformat() if response_row and response_row[1] else None,
                        'created_at': q[5].isoformat() if q[5] else None
                    })
            
            # Calculate rating average
            avg_rating = 0
            if reviews:
                avg_rating = sum(r['rating'] for r in reviews) / len(reviews)
            
            product['reviews'] = reviews
            product['reviews_count'] = len(reviews)
            product['avg_rating'] = round(avg_rating, 1)
            product['queries'] = queries
            
            cur.close()
            conn.close()
            return jsonify(product)
    except Exception as e:
        print(f"Error: {e}")
    
    return jsonify({'error': 'Error fetching product'}), 500

# ========== REVIEWS SYSTEM ==========

@app.route('/api/reviews', methods=['POST'])
@login_required
def create_review():
    """Create product review"""
    data = request.get_json()
    
    if not data or 'product_id' not in data or 'rating' not in data:
        return jsonify({'error': 'Missing fields'}), 400
    
    if not (1 <= data['rating'] <= 5):
        return jsonify({'error': 'Rating must be 1-5'}), 400
    
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO reviews (user_id, product_id, rating, review_text, created_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, user_id, rating, review_text, created_at
            ''', (
                session['user_id'],
                data['product_id'],
                data['rating'],
                data.get('review_text', ''),
                datetime.now()
            ))
            review = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            
            if review:
                return jsonify({
                    'id': review[0],
                    'user_id': review[1],
                    'rating': review[2],
                    'review_text': review[3],
                    'created_at': review[4].isoformat()
                }), 201
    except Exception as e:
        print(f"Error creating review: {e}")
    
    return jsonify({'error': 'Failed to create review'}), 500

# ========== WISHLIST ==========

@app.route('/api/wishlist', methods=['POST'])
@login_required
def add_to_wishlist():
    """Add product to wishlist"""
    data = request.get_json()
    
    if not data or 'product_id' not in data:
        return jsonify({'error': 'Product ID required'}), 400
    
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO wishlist (user_id, product_id, added_at)
                VALUES (%s, %s, %s)
                RETURNING id, user_id, product_id, added_at
            ''', (session['user_id'], data['product_id'], datetime.now()))
            item = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            
            if item:
                return jsonify({
                    'id': item[0],
                    'product_id': item[2],
                    'added_at': item[3].isoformat()
                }), 201
    except Exception as e:
        print(f"Error adding to wishlist: {e}")
    
    return jsonify({'error': 'Failed to add to wishlist'}), 500

@app.route('/api/wishlist/<wishlist_id>', methods=['DELETE'])
@login_required
def remove_from_wishlist(wishlist_id):
    """Remove from wishlist"""
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('DELETE FROM wishlist WHERE id = %s AND user_id = %s',
                       (wishlist_id, session['user_id']))
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({'message': 'Removed from wishlist'})
    except:
        pass
    
    return jsonify({'error': 'Failed to remove'}), 500

@app.route('/api/user/wishlist')
@login_required
def get_user_wishlist():
    """Get user's wishlist"""
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('''
                SELECT w.id, w.product_id, p.name, p.price, p.images 
                FROM wishlist w
                LEFT JOIN products p ON w.product_id = p.product_id
                WHERE w.user_id = %s
                ORDER BY w.added_at DESC
            ''', (session['user_id'],))
            items = cur.fetchall()
            cur.close()
            conn.close()
            
            wishlist = []
            if items:
                for item in items:
                    wishlist.append({
                        'id': item[0],
                        'product_id': item[1],
                        'name': item[2],
                        'price': item[3],
                        'image': item[4][0] if item[4] else None
                    })
            
            return jsonify(wishlist)
    except:
        pass
    
    return jsonify([])

# ========== QUERY SYSTEM ==========

@app.route('/api/queries', methods=['POST'])
@login_required
def create_query():
    """Create product query with optional screenshot"""
    try:
        product_id = request.form.get('product_id')
        question = request.form.get('question')
        
        if not product_id or not question:
            return jsonify({'error': 'Missing fields'}), 400
        
        screenshot_url = None
        if 'screenshot' in request.files:
            file = request.files['screenshot']
            if file and file.filename and allowed_image(file.filename):
                filename = secure_filename(file.filename)
                filename = f"{uuid.uuid4()}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                screenshot_url = f'/uploads/{filename}'
        
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('''
                INSERT INTO product_queries (user_id, product_id, question, screenshot_url, created_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, user_id, product_id, question, screenshot_url, status, created_at
            ''', (session['user_id'], product_id, question, screenshot_url, datetime.now()))
            
            query = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            
            if query:
                return jsonify({
                    'id': query[0],
                    'product_id': query[2],
                    'question': query[3],
                    'screenshot_url': query[4],
                    'status': query[5],
                    'created_at': query[6].isoformat()
                }), 201
    except Exception as e:
        print(f"Error creating query: {e}")
    
    return jsonify({'error': 'Failed to create query'}), 500

@app.route('/api/queries/<query_id>/response', methods=['POST'])
@admin_required
def respond_to_query(query_id):
    """Admin responds to query"""
    data = request.get_json()
    
    if not data or 'response' not in data:
        return jsonify({'error': 'Response text required'}), 400
    
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            
            # Add response
            cur.execute('''
                INSERT INTO query_responses (query_id, admin_response, responded_at)
                VALUES (%s, %s, %s)
                RETURNING id, admin_response, responded_at
            ''', (query_id, data['response'], datetime.now()))
            
            response = cur.fetchone()
            
            # Update query status
            cur.execute('UPDATE product_queries SET status = %s, updated_at = %s WHERE id = %s',
                       ('answered', datetime.now(), query_id))
            
            conn.commit()
            cur.close()
            conn.close()
            
            if response:
                return jsonify({
                    'id': response[0],
                    'response': response[1],
                    'responded_at': response[2].isoformat()
                }), 201
    except Exception as e:
        print(f"Error: {e}")
    
    return jsonify({'error': 'Failed to respond'}), 500

@app.route('/api/admin/queries')
@admin_required
def get_pending_queries():
    """Get pending queries for admin"""
    try:
        conn = get_db_connection()
        if conn:
            cur = conn.cursor()
            cur.execute('''
                SELECT pq.id, pq.user_id, pq.product_id, pq.question, pq.screenshot_url, 
                       pq.status, pq.created_at, u.name, u.email
                FROM product_queries pq
                LEFT JOIN users u ON pq.user_id = u.id
                WHERE pq.status = 'pending'
                ORDER BY pq.created_at DESC
            ''')
            
            queries = cur.fetchall()
            cur.close()
            conn.close()
            
            result = []
            if queries:
                for q in queries:
                    result.append({
                        'id': q[0],
                        'user_id': q[1],
                        'user_name': q[7],
                        'user_email': q[8],
                        'product_id': q[2],
                        'question': q[3],
                        'screenshot_url': q[4],
                        'status': q[5],
                        'created_at': q[6].isoformat()
                    })
            
            return jsonify(result)
    except:
        pass
    
    return jsonify([])

# ========== EXISTING ROUTES (UNCHANGED) ==========

@app.route('/')
def index():
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except:
        return '<h1>index.html not found</h1>', 404

@app.route('/api/products', methods=['GET'])
def get_all_products():
    """Get all products"""
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
                    'created_at': row[10].isoformat() if row[10] else None
                })
            return jsonify(products)
    except:
        pass
    
    return jsonify([])

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
