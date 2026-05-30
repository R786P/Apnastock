import streamlit as st
import json
import os
from datetime import datetime
import hmac
import uuid

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

os.makedirs(DATA_DIR, exist_ok=True)

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

# ========== SESSION MANAGEMENT ==========
def check_password():
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
    layout="wide"
)

# ========== MAIN HEADER ==========
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🏪 Apna Stock")
    st.markdown("**Best Affiliate Deals for You**")

with col2:
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
        
        tab1, tab2, tab3 = st.tabs(["📦 Products", "📋 Orders", "⚙️ Settings"])
        
        with tab1:
            st.subheader("➕ Add New Product")
            with st.form("add_product_form"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Product Name *")
                    price = st.text_input("Price *", placeholder="₹5000")
                with col2:
                    category = st.selectbox("Category", ["Electronics", "Fashion", "Home", "Books", "Sports", "Other"])
                    original_price = st.text_input("Original Price (optional)")
                
                affiliate_link = st.text_input("Affiliate Link *", placeholder="https://amazon.com/...")
                description = st.text_area("Description", height=60)
                
                if st.form_submit_button("➕ Add Product", use_container_width=True):
                    if not name or not price or not affiliate_link:
                        st.error("❌ Missing required fields!")
                    else:
                        products = load_products()
                        products.append({
                            'id': str(uuid.uuid4()),
                            'name': name,
                            'price': price,
                            'original_price': original_price,
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
                            st.markdown(f"**{prod['category']}**")
                        with col2:
                            st.markdown(f"### {prod['name']}")
                            st.markdown(f"**Price:** {prod['price']}")
                            if prod.get('description'):
                                st.markdown(f"*{prod['description'][:100]}*")
                        with col3:
                            if st.button("🔗 Visit", key=f"visit_{prod['id']}", use_container_width=True):
                                st.markdown(f"[Open Link]({prod['affiliate_link']})")
                            if st.button("🗑️ Delete", key=f"del_{prod['id']}", use_container_width=True):
                                products = [p for p in products if p['id'] != prod['id']]
                                save_products(products)
                                st.success("✅ Deleted!")
                                st.rerun()
            else:
                st.info("📦 No products yet")
        
        with tab2:
            st.subheader("📋 All Orders")
            orders = load_orders()
            if orders:
                for order in sorted(orders, key=lambda x: x.get('created_at', ''), reverse=True):
                    with st.container(border=True):
                        st.markdown(f"**Order ID:** `{order.get('id')}`")
                        st.markdown(f"**Customer:** {order.get('customer_name')} | **Status:** {order.get('status')}")
                        st.markdown(f"**Product:** {order.get('product_name')} | **Total:** ₹{order.get('total_price', 0)}")
            else:
                st.info("📋 No orders yet")
        
        with tab3:
            st.subheader("⚙️ Settings")
            st.info(f"🔐 **Admin Password:** `{ADMIN_PASSWORD}`")
            
            products = load_products()
            orders = load_orders()
            st.metric("Total Products", len(products))
            st.metric("Total Orders", len(orders))

# ========== PUBLIC PAGE ==========
else:
    st.divider()
    
    products = load_products()
    categories = ["All"] + sorted(list(set([p.get('category', 'Other') for p in products])))
    
    col1, col2 = st.columns(2)
    with col1:
        selected_category = st.selectbox("🔍 Category", categories)
    with col2:
        search_query = st.text_input("🔎 Search")
    
    st.divider()
    
    filtered_products = products
    if selected_category != "All":
        filtered_products = [p for p in filtered_products if p.get('category') == selected_category]
    if search_query:
        filtered_products = [p for p in filtered_products if search_query.lower() in p['name'].lower()]
    
    if filtered_products:
        cols = st.columns(2)
        for idx, prod in enumerate(filtered_products):
            with cols[idx % 2]:
                with st.container(border=True):
                    st.markdown(f"### {prod['name']}")
                    st.markdown(f"**💰 {prod['price']}**")
                    if prod.get('original_price'):
                        st.markdown(f"~~{prod['original_price']}~~")
                    st.markdown(f"**Category:** {prod.get('category', 'Other')}")
                    if prod.get('description'):
                        st.markdown(f"*{prod['description'][:80]}*")
                    if st.button("🛒 View Deal", key=f"buy_{prod['id']}", use_container_width=True):
                        st.markdown(f"[🔗 Buy Now]({prod['affiliate_link']})")
    else:
        st.info("❌ No products found")

st.divider()
st.markdown("🏪 **Apna Stock** - Best Affiliate Deals | Powered by Streamlit")
