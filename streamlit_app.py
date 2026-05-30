import streamlit as st
import json
import os
from datetime import datetime
import hmac
import uuid
from pathlib import Path

# ========== CONFIGURATION ==========
if 'ADMIN_PASSWORD' in st.secrets:
    ADMIN_PASSWORD = st.secrets['ADMIN_PASSWORD']
else:
    ADMIN_PASSWORD = 'ApnaStock@2026'

if 'FLASK_SECRET_KEY' in st.secrets:
    FLASK_SECRET_KEY = st.secrets['FLASK_SECRET_KEY']
else:
    FLASK_SECRET_KEY = 'secret-2026'

# File paths
DATA_DIR = 'data'
PRODUCTS_FILE = os.path.join(DATA_DIR, 'products.json')
ORDERS_FILE = os.path.join(DATA_DIR, 'orders.json')
ADS_FILE = os.path.join(DATA_DIR, 'ads_config.json')
UPLOAD_FOLDER = 'uploads'

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ========== DATA FUNCTIONS ==========
def load_products():
    try:
        with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_products(products):
    with open(PRODUCTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(products, f, indent=2, ensure_ascii=False)

def load_orders():
    try:
        with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_orders(orders):
    with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(orders, f, indent=2, ensure_ascii=False)

def load_ads():
    try:
        with open(ADS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {'google_adsense_enabled': False, 'google_publisher_id': '', 'sponsor_ads': []}

def save_ads(ads):
    with open(ADS_FILE, 'w', encoding='utf-8') as f:
        json.dump(ads, f, indent=2, ensure_ascii=False)

# ========== SESSION MANAGEMENT ==========
def check_password():
    """Returns `True` if the user had the correct password."""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if not st.session_state.password_correct:
        with st.form("credentials_form"):
            st.write("## 🔐 Admin Login")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if hmac.compare_digest(password, ADMIN_PASSWORD):
                    st.session_state.password_correct = True
                    st.rerun()
                else:
                    st.error("❌ Wrong password!")
        return False
    return True

# ========== PAGE SETUP ==========
st.set_page_config(
    page_title="🏪 Apna Stock",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main { padding: 0rem 1rem; }
    header { visibility: hidden; }
    footer { visibility: hidden; }
    .product-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 1rem;
        background: white;
    }
</style>
""", unsafe_allow_html=True)

# ========== MAIN HEADER ==========
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.title("🏪 Apna Stock")
    st.markdown("**Best Affiliate Deals for You**")

with col3:
    if st.button("🔐 Admin Panel", use_container_width=True):
        st.session_state.admin_mode = True

# ========== ADMIN PANEL ==========
if st.session_state.get('admin_mode', False):
    st.divider()
    if check_password():
        st.success("✅ Admin Logged In!")
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.password_correct = False
            st.session_state.admin_mode = False
            st.rerun()
        
        admin_tab1, admin_tab2, admin_tab3 = st.tabs(
            ["📦 Products", "📋 Orders", "⚙️ Settings"]
        )
        
        # ===== PRODUCTS TAB =====
        with admin_tab1:
            st.subheader("➕ Add New Product")
            with st.form("add_product_form"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Product Name *", placeholder="e.g., iPhone 15")
                    price = st.text_input("Price (e.g., ₹50000) *", placeholder="₹")
                with col2:
                    category = st.selectbox("Category", ["Electronics", "Fashion", "Home", "Books", "Sports", "Other"])
                    original_price = st.text_input("Original Price (optional)", placeholder="₹")
                
                affiliate_link = st.text_input("Affiliate Link *", placeholder="https://amazon.com/...")
                description = st.text_area("Description", height=80, placeholder="Product details...")
                
                images = st.file_uploader("Upload Images (Max 5)", type=['png', 'jpg', 'jpeg', 'gif', 'webp'], accept_multiple_files=True)
                
                if st.form_submit_button("➕ Add Product", use_container_width=True):
                    if not name or not price or not affiliate_link:
                        st.error("❌ Missing required fields!")
                    elif len(images) == 0:
                        st.error("❌ Please upload at least 1 image!")
                    elif len(images) > 5:
                        st.error("❌ Maximum 5 images allowed!")
                    else:
                        # Save images
                        image_paths = []
                        for img in images:
                            img_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}_{img.name}")
                            with open(img_path, 'wb') as f:
                                f.write(img.getbuffer())
                            image_paths.append(img_path)
                        
                        # Add product
                        products = load_products()
                        products.append({
                            'id': str(uuid.uuid4()),
                            'name': name,
                            'price': price,
                            'original_price': original_price,
                            'images': image_paths,
                            'affiliate_link': affiliate_link,
                            'category': category,
                            'description': description,
                            'active': True,
                            'created_at': datetime.now().isoformat()
                        })
                        save_products(products)
                        st.success("✅ Product added successfully!")
                        st.rerun()
            
            st.divider()
            st.subheader("📦 All Products")
            products = load_products()
            if products:
                for prod in reversed(products):
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([1, 3, 1])
                        with col1:
                            if prod.get('images'):
                                try:
                                    st.image(prod['images'][0], width=150)
                                except:
                                    st.write("📷 Image")
                        with col2:
                            st.markdown(f"### {prod['name']}")
                            st.markdown(f"**Price:** {prod['price']}")
                            st.markdown(f"**Category:** {prod['category']}")
                            if prod.get('description'):
                                st.markdown(f"*{prod['description'][:100]}...*")
                        with col3:
                            if st.button("🔗 Visit", key=f"visit_{prod['id']}", use_container_width=True):
                                st.markdown(f"[Open Link]({prod['affiliate_link']})")
                            if st.button("🗑️ Delete", key=f"del_{prod['id']}", use_container_width=True):
                                products = [p for p in products if p['id'] != prod['id']]
                                save_products(products)
                                st.success("✅ Deleted!")
                                st.rerun()
            else:
                st.info("📦 No products yet. Add your first product above!")
        
        # ===== ORDERS TAB =====
        with admin_tab2:
            st.subheader("📋 All Orders")
            orders = load_orders()
            if orders:
                for order in sorted(orders, key=lambda x: x.get('created_at', ''), reverse=True):
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([2, 2, 1.5])
                        with col1:
                            st.markdown(f"**Order ID:** `{order.get('id')}`")
                            st.markdown(f"**Customer:** {order.get('customer_name')}")
                            st.markdown(f"**Email:** {order.get('customer_email', 'N/A')}")
                        with col2:
                            st.markdown(f"**Product:** {order.get('product_name')}")
                            st.markdown(f"**Qty:** {order.get('quantity')}")
                            st.markdown(f"**Total:** ₹{order.get('total_price', 0)}")
                        with col3:
                            st.markdown(f"**Status:** `{order.get('status')}`")
                            new_status = st.selectbox(
                                "Change Status",
                                ["pending", "confirmed", "shipped", "delivered", "cancelled"],
                                index=["pending", "confirmed", "shipped", "delivered", "cancelled"].index(order.get('status', 'pending')),
                                key=f"status_{order['id']}"
                            )
                            if st.button("✅ Update", key=f"update_{order['id']}", use_container_width=True):
                                order['status'] = new_status
                                order['updated_at'] = datetime.now().isoformat()
                                save_orders(orders)
                                st.success("✅ Order updated!")
                                st.rerun()
            else:
                st.info("📋 No orders yet")
        
        # ===== SETTINGS TAB =====
        with admin_tab3:
            st.subheader("⚙️ Settings")
            
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"🔐 **Admin Password:**\n`{ADMIN_PASSWORD}`")
            with col2:
                st.warning("To change credentials, update `.streamlit/secrets.toml`")
            
            st.divider()
            st.subheader("📊 Statistics")
            products = load_products()
            orders = load_orders()
            
            stat1, stat2, stat3 = st.columns(3)
            with stat1:
                st.metric("Total Products", len(products))
            with stat2:
                st.metric("Total Orders", len(orders))
            with stat3:
                total_revenue = sum([o.get('total_price', 0) for o in orders])
                st.metric("Total Revenue", f"₹{total_revenue}")

# ========== PUBLIC PAGE ==========
else:
    st.divider()
    
    col1, col2, col3 = st.columns([1, 1, 3])
    
    products = load_products()
    categories = ["All"] + sorted(list(set([p.get('category', 'Other') for p in products])))
    
    with col1:
        selected_category = st.selectbox("🔍 Filter by Category", categories)
    
    with col2:
        search_query = st.text_input("🔎 Search Products")
    
    st.divider()
    
    # Filter products
    filtered_products = products
    
    if selected_category != "All":
        filtered_products = [p for p in filtered_products if p.get('category') == selected_category]
    
    if search_query:
        filtered_products = [p for p in filtered_products if search_query.lower() in p['name'].lower()]
    
    if filtered_products:
        cols = st.columns(3)
        for idx, prod in enumerate(filtered_products):
            with cols[idx % 3]:
                with st.container(border=True):
                    # Image
                    if prod.get('images'):
                        try:
                            st.image(prod['images'][0], use_column_width=True)
                        except:
                            st.write("📷 Image not available")
                    
                    # Product details
                    st.markdown(f"### {prod['name']}")
                    
                    price_str = str(prod['price']).replace('₹', '').strip()
                    st.markdown(f"**💰 ₹{price_str}**")
                    
                    if prod.get('original_price'):
                        orig_str = str(prod['original_price']).replace('₹', '').strip()
                        try:
                            discount = int(((float(orig_str) - float(price_str)) / float(orig_str)) * 100)
                            st.markdown(f"~~₹{orig_str}~~ **-{discount}%**")
                        except:
                            st.markdown(f"~~₹{orig_str}~~")
                    
                    st.markdown(f"**Category:** {prod.get('category', 'Other')}")
                    
                    if prod.get('description'):
                        st.markdown(f"*{prod['description'][:60]}...*")
                    
                    if st.button("🛒 View Deal", key=f"buy_{prod['id']}", use_container_width=True):
                        st.markdown(f"[🔗 Click to buy on Amazon]({prod['affiliate_link']})")
    else:
        if search_query or selected_category != "All":
            st.info("❌ No products found matching your filters")
        else:
            st.info("📦 No products available yet")

# ========== FOOTER ==========
st.divider()
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.85rem; padding: 1rem;">
    <p>🏪 <strong>Apna Stock</strong> - Best Affiliate Deals | © 2026</p>
    <p style="font-size: 0.75rem;">Powered by Streamlit</p>
</div>
""", unsafe_allow_html=True)
