import os
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, redirect, session
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine, Column, String, DateTime, Integer, Float, JSON as SQLJSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

app = Flask(__name__)

app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'secret-2026')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'ApnaStock@2026')

# ==================== DATABASE SETUP ====================
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://neondb_owner:npg_tj8TKabiskd3@ep-misty-wave-ap0gqj6j-pooler.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require')

# Remove sslmode and channel_binding for local testing if needed
if 'localhost' in DATABASE_URL or '127.0.0.1' in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.split('?')[0]

engine = create_engine(DATABASE_URL, poolclass=NullPool)
Base = declarative_base()
Session = sessionmaker(bind=engine)

# ==================== MODELS ====================
class Product(Base):
    __tablename__ = "products"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(String, nullable=False)
    original_price = Column(String)
    affiliate_link = Column(String, nullable=False)
    category = Column(String, default='other')
    description = Column(String)
    images = Column(SQLJSON)
    active = Column(String, default='true')
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime)

class Order(Base):
    __tablename__ = "orders"
    id = Column(String, primary_key=True)
    order_number = Column(Integer)
    customer_name = Column(String, nullable=False)
    customer_email = Column(String)
    customer_phone = Column(String)
    product_id = Column(String, nullable=False)
    product_name = Column(String)
    product_price = Column(String)
    quantity = Column(Integer, default=1)
    total_price = Column(Float)
    status = Column(String, default='pending')
    shipping_address = Column(String)
    tracking_number = Column(String)
    notes = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime)

class Template(Base):
    __tablename__ = "templates"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    colors = Column(SQLJSON)
    fonts = Column(SQLJSON)
    layout = Column(String, default='grid')
    created_at = Column(DateTime, default=datetime.now)

class AdsConfig(Base):
    __tablename__ = "ads_config"
    id = Column(String, primary_key=True, default='config')
    google_adsense_enabled = Column(String, default='false')
    google_publisher_id = Column(String)
    sponsor_ads = Column(SQLJSON, default=list)

# Create tables
Base.metadata.create_all(engine)

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

# ==================== HELPER FUNCTIONS ====================
def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXT

def allowed_music(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_MUSIC_EXT

def init_db():
    """Initialize database with default config"""
    db = Session()
    try:
        existing = db.query(AdsConfig).filter_by(id='config').first()
        if not existing:
            config = AdsConfig(
                id='config',
                google_adsense_enabled='false',
                google_publisher_id='',
                sponsor_ads=[]
            )
            db.add(config)
            db.commit()
    except Exception as e:
        print(f"Error initializing DB: {e}")
        db.rollback()
    finally:
        db.close()

init_db()

# ==================== ROUTES ====================
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

# ==================== PRODUCTS API ====================
@app.route('/api/products', methods=['GET'])
def get_all_products():
    db = Session()
    try:
        cat = request.args.get('category', 'all')
        query = db.query(Product)
        
        if cat != 'all':
            query = query.filter_by(category=cat)
        
        products = query.order_by(Product.created_at.desc()).all()
        
        result = []
        for p in products:
            result.append({
                'id': p.id,
                'name': p.name,
                'price': p.price,
                'original_price': p.original_price or '',
                'images': p.images or [],
                'affiliate_link': p.affiliate_link,
                'category': p.category,
                'description': p.description or '',
                'active': p.active,
                'created_at': p.created_at.isoformat() if p.created_at else ''
            })
        
        return jsonify(result)
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/products', methods=['POST'])
def add_product():
    db = Session()
    try:
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
        
        prod = Product(
            id=str(uuid.uuid4()),
            name=name,
            price=price,
            original_price=original_price,
            images=images,
            affiliate_link=affiliate_link,
            category=category,
            description=description,
            active='true',
            created_at=datetime.now()
        )
        
        db.add(prod)
        db.commit()
        
        return jsonify({
            'message': 'Added',
            'product': {
                'id': prod.id,
                'name': prod.name,
                'price': prod.price,
                'original_price': prod.original_price or '',
                'images': prod.images or [],
                'affiliate_link': prod.affiliate_link,
                'category': prod.category,
                'description': prod.description,
                'active': prod.active,
                'created_at': prod.created_at.isoformat()
            }
        }), 201
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/products/<pid>', methods=['GET'])
def get_product(pid):
    db = Session()
    try:
        prod = db.query(Product).filter_by(id=pid).first()
        if prod:
            return jsonify({
                'id': prod.id,
                'name': prod.name,
                'price': prod.price,
                'original_price': prod.original_price or '',
                'images': prod.images or [],
                'affiliate_link': prod.affiliate_link,
                'category': prod.category,
                'description': prod.description,
                'active': prod.active,
                'created_at': prod.created_at.isoformat() if prod.created_at else ''
            })
        return jsonify({'error': 'Not found'}), 404
    finally:
        db.close()

@app.route('/api/products/<pid>', methods=['PUT'])
def edit_product(pid):
    db = Session()
    try:
        prod = db.query(Product).filter_by(id=pid).first()
        if not prod:
            return jsonify({'error': 'Not found'}), 404
        
        name = request.form.get('name')
        price = request.form.get('price')
        affiliate_link = request.form.get('affiliate_link')
        category = request.form.get('category', 'other')
        description = request.form.get('description', '')
        original_price = request.form.get('original_price', '')
        
        images = prod.images or []
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
        
        prod.name = name or prod.name
        prod.price = price or prod.price
        prod.affiliate_link = affiliate_link or prod.affiliate_link
        prod.category = category
        prod.description = description
        prod.original_price = original_price
        prod.images = images
        prod.updated_at = datetime.now()
        
        db.commit()
        
        return jsonify({
            'message': 'Updated',
            'product': {
                'id': prod.id,
                'name': prod.name,
                'price': prod.price,
                'original_price': prod.original_price or '',
                'images': prod.images or [],
                'affiliate_link': prod.affiliate_link,
                'category': prod.category,
                'description': prod.description,
                'active': prod.active,
                'updated_at': prod.updated_at.isoformat() if prod.updated_at else ''
            }
        }), 200
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/products/<pid>', methods=['DELETE'])
def del_product(pid):
    db = Session()
    try:
        prod = db.query(Product).filter_by(id=pid).first()
        if prod:
            for img in prod.images or []:
                if img.startswith('/uploads/'):
                    try:
                        os.remove(img.replace('/uploads/', UPLOAD_FOLDER + '/'))
                    except:
                        pass
        
        db.query(Product).filter_by(id=pid).delete()
        db.commit()
        
        return jsonify({'message': 'Deleted'}), 200
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

# ==================== ORDERS API ====================
@app.route('/api/orders', methods=['GET'])
def get_all_orders():
    db = Session()
    try:
        orders = db.query(Order).order_by(Order.created_at.desc()).all()
        
        result = []
        for o in orders:
            result.append({
                'id': o.id,
                'order_number': o.order_number,
                'customer_name': o.customer_name,
                'customer_email': o.customer_email or '',
                'customer_phone': o.customer_phone or '',
                'product_id': o.product_id,
                'product_name': o.product_name,
                'product_price': o.product_price,
                'quantity': o.quantity,
                'total_price': o.total_price,
                'status': o.status,
                'shipping_address': o.shipping_address or '',
                'tracking_number': o.tracking_number,
                'created_at': o.created_at.isoformat() if o.created_at else '',
                'updated_at': o.updated_at.isoformat() if o.updated_at else ''
            })
        
        return jsonify(result)
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/orders', methods=['POST'])
def create_order():
    db = Session()
    try:
        data = request.get_json()
        
        if not data or not all(k in data for k in ['customer_name', 'product_id', 'quantity']):
            return jsonify({'error': 'Missing fields'}), 400
        
        product = db.query(Product).filter_by(id=data.get('product_id')).first()
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        order_count = db.query(Order).count() + 1
        
        order = Order(
            id=f"ORD{str(uuid.uuid4())[:8].upper()}",
            order_number=order_count,
            customer_name=data.get('customer_name'),
            customer_email=data.get('customer_email', ''),
            customer_phone=data.get('customer_phone', ''),
            product_id=data.get('product_id'),
            product_name=product.name,
            product_price=product.price,
            quantity=data.get('quantity'),
            total_price=float(product.price.replace('₹', '').strip()) * int(data.get('quantity', 1)),
            status='pending',
            shipping_address=data.get('shipping_address', ''),
            tracking_number=f"TRK{str(uuid.uuid4())[:12].upper()}",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        db.add(order)
        db.commit()
        
        return jsonify({
            'message': 'Order created',
            'order': {
                'id': order.id,
                'order_number': order.order_number,
                'customer_name': order.customer_name,
                'product_name': order.product_name,
                'quantity': order.quantity,
                'total_price': order.total_price,
                'status': order.status,
                'tracking_number': order.tracking_number,
                'created_at': order.created_at.isoformat()
            }
        }), 201
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    db = Session()
    try:
        order = db.query(Order).filter_by(id=order_id).first()
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        return jsonify({
            'id': order.id,
            'order_number': order.order_number,
            'customer_name': order.customer_name,
            'customer_email': order.customer_email or '',
            'customer_phone': order.customer_phone or '',
            'product_name': order.product_name,
            'quantity': order.quantity,
            'total_price': order.total_price,
            'status': order.status,
            'tracking_number': order.tracking_number,
            'created_at': order.created_at.isoformat() if order.created_at else ''
        })
    finally:
        db.close()

@app.route('/api/orders/<order_id>', methods=['PUT'])
def update_order_status(order_id):
    db = Session()
    try:
        data = request.get_json()
        
        if 'status' not in data:
            return jsonify({'error': 'Status required'}), 400
        
        valid_statuses = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']
        if data['status'] not in valid_statuses:
            return jsonify({'error': 'Invalid status'}), 400
        
        order = db.query(Order).filter_by(id=order_id).first()
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        order.status = data['status']
        order.updated_at = datetime.now()
        
        if 'notes' in data:
            order.notes = data['notes']
        
        db.commit()
        
        return jsonify({
            'message': 'Order updated',
            'order': {
                'id': order.id,
                'status': order.status,
                'updated_at': order.updated_at.isoformat()
            }
        })
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/orders/track/<tracking_number>', methods=['GET'])
def track_order(tracking_number):
    db = Session()
    try:
        order = db.query(Order).filter_by(tracking_number=tracking_number).first()
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        return jsonify({
            'id': order.id,
            'order_number': order.order_number,
            'customer_name': order.customer_name,
            'product_name': order.product_name,
            'quantity': order.quantity,
            'total_price': order.total_price,
            'status': order.status,
            'tracking_number': order.tracking_number,
            'created_at': order.created_at.isoformat() if order.created_at else ''
        })
    finally:
        db.close()

@app.route('/api/orders/<order_id>', methods=['DELETE'])
def delete_order(order_id):
    db = Session()
    try:
        db.query(Order).filter_by(id=order_id).delete()
        db.commit()
        return jsonify({'message': 'Deleted'})
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

# ==================== TEMPLATES API ====================
@app.route('/api/templates', methods=['GET'])
def get_all_templates():
    db = Session()
    try:
        templates = db.query(Template).all()
        
        result = []
        for t in templates:
            result.append({
                'id': t.id,
                'name': t.name,
                'colors': t.colors or {},
                'fonts': t.fonts or {},
                'layout': t.layout,
                'created_at': t.created_at.isoformat() if t.created_at else ''
            })
        
        return jsonify(result)
    finally:
        db.close()

@app.route('/api/templates', methods=['POST'])
def add_template():
    db = Session()
    try:
        data = request.get_json()
        if not data or 'name' not in data or 'colors' not in data:
            return jsonify({'error': 'Missing fields'}), 400
        
        template = Template(
            id=str(uuid.uuid4()),
            name=data.get('name'),
            colors=data.get('colors'),
            fonts=data.get('fonts', {}),
            layout=data.get('layout', 'grid'),
            created_at=datetime.now()
        )
        
        db.add(template)
        db.commit()
        
        return jsonify({
            'message': 'Added',
            'template': {
                'id': template.id,
                'name': template.name,
                'colors': template.colors,
                'layout': template.layout
            }
        }), 201
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/templates/<tid>', methods=['DELETE'])
def del_template(tid):
    db = Session()
    try:
        db.query(Template).filter_by(id=tid).delete()
        db.commit()
        return jsonify({'message': 'Deleted'})
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

# ==================== MUSIC API ====================
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

# ==================== ADS API ====================
@app.route('/api/ads/config', methods=['GET'])
def get_ads_cfg():
    db = Session()
    try:
        cfg = db.query(AdsConfig).filter_by(id='config').first()
        if cfg:
            return jsonify({
                'google_adsense_enabled': cfg.google_adsense_enabled == 'true',
                'google_publisher_id': cfg.google_publisher_id or '',
                'sponsor_ads': cfg.sponsor_ads or []
            })
        return jsonify({
            'google_adsense_enabled': False,
            'google_publisher_id': '',
            'sponsor_ads': []
        })
    finally:
        db.close()

@app.route('/api/ads/config', methods=['POST'])
def update_ads_cfg():
    db = Session()
    try:
        data = request.get_json()
        cfg = db.query(AdsConfig).filter_by(id='config').first()
        
        if not cfg:
            cfg = AdsConfig(id='config')
            db.add(cfg)
        
        if 'google_adsense_enabled' in data:
            cfg.google_adsense_enabled = 'true' if data['google_adsense_enabled'] else 'false'
        if 'google_publisher_id' in data:
            cfg.google_publisher_id = data['google_publisher_id']
        
        db.commit()
        
        return jsonify({
            'message': 'Updated',
            'config': {
                'google_adsense_enabled': cfg.google_adsense_enabled == 'true',
                'google_publisher_id': cfg.google_publisher_id or ''
            }
        })
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/ads/sponsor', methods=['POST'])
def add_sponsor():
    db = Session()
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ['company_name', 'image_url', 'ad_link']):
            return jsonify({'error': 'Missing'}), 400
        
        cfg = db.query(AdsConfig).filter_by(id='config').first()
        if not cfg:
            cfg = AdsConfig(id='config', sponsor_ads=[])
            db.add(cfg)
        
        sponsor = {
            'id': str(uuid.uuid4()),
            'company_name': data.get('company_name'),
            'image_url': data.get('image_url'),
            'ad_link': data.get('ad_link'),
            'position': data.get('position', 'banner_top'),
            'active': True,
            'created_at': datetime.now().isoformat()
        }
        
        if cfg.sponsor_ads is None:
            cfg.sponsor_ads = []
        cfg.sponsor_ads.append(sponsor)
        
        db.commit()
        
        return jsonify({'message': 'Added', 'sponsor': sponsor}), 201
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/ads/sponsor/<sid>', methods=['DELETE'])
def del_sponsor(sid):
    db = Session()
    try:
        cfg = db.query(AdsConfig).filter_by(id='config').first()
        if cfg and cfg.sponsor_ads:
            cfg.sponsor_ads = [s for s in cfg.sponsor_ads if s.get('id') != sid]
            db.commit()
        
        return jsonify({'message': 'Deleted'})
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

# ==================== FILE SERVING ====================
@app.route('/uploads/<filename>')
def serve_image(filename):
    try:
        return open(os.path.join(UPLOAD_FOLDER, filename), 'rb'), 200, {'Content-Type': 'image/*'}
    except:
        return jsonify({'error': 'Not found'}), 404

@app.route('/music/<filename>')
def serve_music(filename):
    try:
        return open(os.path.join(MUSIC_FOLDER, filename), 'rb'), 200, {'Content-Type': 'audio/*'}
    except:
        return jsonify({'error': 'Not found'}), 404

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
