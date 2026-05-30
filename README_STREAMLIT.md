# 🏪 Apna Stock - Streamlit Version

**Best Affiliate Deals Platform - Now on Streamlit!**

## 🚀 Features

✅ **Admin Panel** - Add, edit, delete products  
✅ **Product Management** - Organize by categories  
✅ **Order Tracking** - Manage customer orders  
✅ **Image Upload** - Upload up to 5 images per product  
✅ **Affiliate Links** - Integrated affiliate link management  
✅ **Search & Filter** - Find products by category or name  
✅ **Responsive Design** - Works on mobile, tablet, desktop  

---

## 📋 Environment Variables Required

| Variable | Description | Default |
|----------|-------------|----------|
| `ADMIN_PASSWORD` | Admin panel password | `ApnaStock@2026` |
| `FLASK_SECRET_KEY` | Session secret key | `secret-2026` |

---

## 🏃 Local Setup

### 1. Clone Repository
```bash
git clone https://github.com/R786P/Apnastock.git
cd Apnastock
git checkout streamlit-conversion
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Locally
```bash
streamlit run streamlit_app.py
```

App will open at: `http://localhost:8501`

---

## 🌐 Deploy on Streamlit Cloud

### Step 1: Push Code to GitHub
```bash
git add .
git commit -m "Streamlit conversion ready for deployment"
git push origin streamlit-conversion
```

### Step 2: Create PR to Merge
```bash
# Create a Pull Request on GitHub to merge streamlit-conversion → main
```

### Step 3: Deploy on Streamlit Cloud

1. Go to [Streamlit Cloud](https://share.streamlit.io)
2. Click **"New app"**
3. Connect your GitHub account
4. Select:
   - **Repository:** `R786P/Apnastock`
   - **Branch:** `streamlit-conversion` (or `main` after merging)
   - **Main file:** `streamlit_app.py`
5. Click **"Deploy"**

### Step 4: Add Secrets

1. After deployment, click **⋮ → Settings**
2. Go to **"Secrets"** tab
3. Add:
```toml
ADMIN_PASSWORD = "ApnaStock@2026"
FLASK_SECRET_KEY = "your-secure-secret-key-2026"
```
4. Click **"Save"** ✅

---

## 📂 File Structure

```
Apnastock/
├── streamlit_app.py          # Main Streamlit app
├── requirements.txt          # Python dependencies
├── .streamlit/
│   ├── config.toml          # Streamlit configuration
│   └── secrets.toml         # Local secrets (git-ignored)
├── data/
│   ├── products.json        # Products database
│   ├── orders.json          # Orders database
│   └── ads_config.json      # Ads configuration
├── uploads/                 # Product images folder
└── README_STREAMLIT.md      # This file
```

---

## 🔐 Admin Login

**Default Password:** `ApnaStock@2026`

### Access Admin Panel

1. Click **🔐 Admin Panel** button
2. Enter password
3. Manage:
   - 📦 **Products** - Add/edit/delete products
   - 📋 **Orders** - Track and update order status
   - ⚙️ **Settings** - View configuration & statistics

---

## 📦 Adding Products

1. Go to **Admin Panel → Products**
2. Fill in:
   - Product Name
   - Price (e.g., ₹5000)
   - Category
   - Affiliate Link
   - Description
   - Upload 1-5 images
3. Click **"➕ Add Product"**

---

## 🛒 Customer Features

- **Browse Products** - View all products with images
- **Filter** - Filter by category or search by name
- **View Deals** - Click "🛒 View Deal" to visit affiliate link
- **Pricing** - Shows original price, discount percentage

---

## 🐛 Troubleshooting

### Issue: Admin Panel shows "Wrong password"
**Solution:** Check `.streamlit/secrets.toml` (local) or Streamlit Cloud Settings (online)

### Issue: Images not loading
**Solution:** Ensure `uploads/` folder exists in the same directory as `streamlit_app.py`

### Issue: Deployment fails
**Solution:** Ensure `requirements.txt` has correct dependencies and no syntax errors in code

---

## 🤝 Contributing

Feel free to fork and submit pull requests!

---

## 📄 License

MIT License - Feel free to use for personal/commercial projects

---

**Made with ❤️ using Streamlit**
