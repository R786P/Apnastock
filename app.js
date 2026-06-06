async function loadProducts(category = 'all') {
    const grid = document.getElementById('productsGrid');
    grid.innerHTML = '<div class="loading">Loading deals... 🛍️</div>';
    
    try {
        const url = category === 'all' ? '/api/products' : `/api/products?category=${category}`;
        const res = await fetch(url);
        const products = await res.json();
        
        console.log('Products loaded:', products);
        
        if (products.length === 0) {
            grid.innerHTML = '<p style="text-align:center; grid-column:1/-1;">No products found. Check back soon! 😊</p>';
            return;
        }
        
        showDealOfTheDay(products);
        grid.innerHTML = products.map(product => createProductCard(product)).join('');
        
    } catch (error) {
        console.error('Error loading products:', error);
        grid.innerHTML = '<p style="text-align:center; grid-column:1/-1; color:#e74c3c;">Failed to load products. Please refresh. 🔄</p>';
    }
}

function createProductCard(p) {
    const discount = p.original_price ? calculateDiscount(p.price, p.original_price) : null;
    const dealBadge = p.deal_type === 'lightning' ? '⚡ Lightning' : 
                      p.deal_type === 'hot' ? '🔥 Hot' : null;
    
    // FIX: Handle both 'image' (string) and 'images' (array) formats
    let imageUrl = 'https://via.placeholder.com/300x200?text=No+Image';
    if (p.image) {
        imageUrl = p.image;
    } else if (p.images && Array.isArray(p.images) && p.images.length > 0) {
        imageUrl = p.images[0];
    } else if (p.images && typeof p.images === 'string') {
        imageUrl = p.images;
    }
    
    // FIX: Show full product details without scrolling - expandable card
    return `
        <article class="product-card" onclick="showProductDetails(${JSON.stringify(p).replace(/"/g, '&quot;')})">
            ${dealBadge ? `<span class="deal-badge">${dealBadge}</span>` : ''}
            <div class="product-image-container">
                <img src="${imageUrl}" alt="${p.name}" class="product-image" 
                     onerror="this.src='https://via.placeholder.com/300x200?text=No+Image'">
            </div>
            <div class="product-info">
                <h3>${p.name}</h3>
                <p class="product-desc">${p.description || 'Great product with amazing features!'}</p>
                <div class="price-section">
                    <span class="price">${p.price}</span>
                    ${p.original_price ? `<span class="original-price">${p.original_price}</span>` : ''}
                    ${discount ? `<span class="discount">(${discount}% OFF)</span>` : ''}
                </div>
                <div class="product-actions">
                    <button class="btn-view" onclick="event.stopPropagation(); showProductDetails(${JSON.stringify(p).replace(/"/g, '&quot;')})">📋 View Details</button>
                    <a href="${p.affiliate_link}" target="_blank" rel="noopener noreferrer" class="btn-buy" onclick="event.stopPropagation()">🛒 Buy Now</a>
                    <button class="btn-view" onclick="event.stopPropagation(); openEditModal('${p.id}')" style="background: #3498db;">✏️ Edit</button>
                </div>
            </div>
        </article>
    `;
}

function showProductDetails(product) {
    const modal = document.createElement('div');
    modal.className = 'product-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <span class="modal-close" onclick="this.parentElement.parentElement.remove()">&times;</span>
            <div class="modal-body">
                <div class="modal-images">
                    ${product.images && Array.isArray(product.images) ? 
                        `<img src="${product.images[0]}" alt="${product.name}" class="modal-main-image">` :
                        `<img src="https://via.placeholder.com/400x400?text=No+Image" alt="${product.name}" class="modal-main-image">`
                    }
                </div>
                <div class="modal-info">
                    <h2>${product.name}</h2>
                    <p class="modal-category">Category: <strong>${product.category || 'General'}</strong></p>
                    <p class="modal-description">${product.description || 'Amazing product with great features!'}</p>
                    
                    <div class="modal-price">
                        <span class="modal-price-current">${product.price}</span>
                        ${product.original_price ? `<span class="modal-price-original">${product.original_price}</span>` : ''}
                    </div>
                    
                    <div class="modal-details">
                        <h4>📦 Product Details:</h4>
                        <ul>
                            <li><strong>Price:</strong> ${product.price}</li>
                            ${product.original_price ? `<li><strong>Original Price:</strong> ${product.original_price}</li>` : ''}
                            <li><strong>Category:</strong> ${product.category || 'General'}</li>
                            <li><strong>Status:</strong> ${product.active ? '✅ Available' : '❌ Out of Stock'}</li>
                        </ul>
                    </div>
                    
                    <div class="modal-actions">
                        <a href="${product.affiliate_link}" target="_blank" rel="noopener noreferrer" class="modal-btn-buy">
                            🛒 Buy Now on Affiliate Site
                        </a>
                        <button class="modal-btn-close" onclick="this.closest('.product-modal').remove()">
                            ✕ Close
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

function calculateDiscount(current, original) {
    const curr = parseFloat(current.replace(/[^0-9.]/g, ''));
    const orig = parseFloat(original.replace(/[^0-9.]/g, ''));
    if (curr && orig && orig > curr) {
        return Math.round((1 - curr/orig) * 100);
    }
    return null;
}

function showDealOfTheDay(products) {
    const deals = products.filter(p => p.deal_type !== 'normal');
    const banner = document.getElementById('dealBanner');
    
    if (deals.length > 0) {
        const today = new Date().toDateString();
        const index = Math.abs(hashCode(today)) % deals.length;
        const deal = deals[index];
        
        // FIX: Get first image from images array
        let dealImage = 'https://via.placeholder.com/300x200?text=Deal';
        if (deal.image) {
            dealImage = deal.image;
        } else if (deal.images && Array.isArray(deal.images) && deal.images.length > 0) {
            dealImage = deal.images[0];
        }
        
        document.getElementById('dealContent').innerHTML = `
            <h4>${deal.name}</h4>
            <div class="price">${deal.price} 
                ${deal.original_price ? `<s style="font-size:0.9rem">${deal.original_price}</s>` : ''}
            </div>
            <a href="${deal.affiliate_link}" target="_blank" class="buy-btn" style="padding:0.4rem 1rem; font-size:0.9rem; margin-top:0.5rem; display:inline-block; width:auto;">
                Grab Deal →
            </a>
        `;
        banner.style.display = 'flex';
    } else {
        banner.style.display = 'none';
    }
}

function hashCode(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = ((hash << 5) - hash) + str.charCodeAt(i);
        hash |= 0;
    }
    return hash;
}

function filterProducts(category) {
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
        if(btn.dataset.category === category) {
            btn.classList.add('active');
        }
    });
    loadProducts(category);
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function subscribeNewsletter(e) {
    e.preventDefault();
    alert('Thank you for subscribing! 🎉\n\nFeature coming soon - We will notify you about daily deals!');
    e.target.reset();
}

document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        loadProducts(e.target.dataset.category);
    });
});

document.addEventListener('DOMContentLoaded', () => {
    loadProducts();
});

// Add CSS for modal
const style = document.createElement('style');
style.textContent = `
    .product-modal {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
        padding: 1rem;
    }
    
    .modal-content {
        background: white;
        border-radius: 12px;
        max-width: 600px;
        width: 100%;
        max-height: 90vh;
        overflow-y: auto;
        position: relative;
    }
    
    .modal-close {
        position: absolute;
        top: 1rem;
        right: 1rem;
        font-size: 2rem;
        cursor: pointer;
        background: #f0f0f0;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    }
    
    .modal-body {
        padding: 2rem 1.5rem;
    }
    
    .modal-images {
        margin-bottom: 1.5rem;
        text-align: center;
    }
    
    .modal-main-image {
        max-width: 100%;
        height: auto;
        border-radius: 8px;
        max-height: 300px;
    }
    
    .modal-info h2 {
        margin: 0 0 1rem 0;
        color: #333;
        font-size: 1.5rem;
    }
    
    .modal-category {
        color: #666;
        margin-bottom: 1rem;
    }
    
    .modal-description {
        color: #555;
        line-height: 1.6;
        margin-bottom: 1.5rem;
    }
    
    .modal-price {
        font-size: 1.3rem;
        margin-bottom: 1.5rem;
    }
    
    .modal-price-current {
        color: #e74c3c;
        font-weight: bold;
        margin-right: 1rem;
    }
    
    .modal-price-original {
        text-decoration: line-through;
        color: #999;
    }
    
    .modal-details {
        background: #f9f9f9;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
    }
    
    .modal-details h4 {
        margin-top: 0;
        color: #333;
    }
    
    .modal-details ul {
        list-style: none;
        padding: 0;
        margin: 0;
    }
    
    .modal-details li {
        padding: 0.5rem 0;
        border-bottom: 1px solid #eee;
        color: #555;
    }
    
    .modal-details li:last-child {
        border-bottom: none;
    }
    
    .modal-actions {
        display: flex;
        gap: 1rem;
        flex-direction: column;
    }
    
    .modal-btn-buy {
        display: block;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        text-align: center;
        border-radius: 8px;
        text-decoration: none;
        font-weight: bold;
        cursor: pointer;
    }
    
    .modal-btn-buy:hover {
        opacity: 0.9;
    }
    
    .modal-btn-close {
        background: #f0f0f0;
        color: #333;
        padding: 0.75rem;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        font-weight: bold;
    }
    
    .product-image-container {
        width: 100%;
        height: 200px;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #f9f9f9;
    }
    
    .product-image {
        max-width: 100%;
        max-height: 100%;
        width: auto;
        height: auto;
    }
    
    .product-desc {
        color: #666;
        font-size: 0.9rem;
        line-height: 1.4;
        margin: 0.5rem 0 1rem 0;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    
    .product-actions {
        display: flex;
        gap: 0.5rem;
        margin-top: 1rem;
    }
    
    .btn-view, .btn-buy {
        flex: 1;
        padding: 0.5rem;
        border: none;
        border-radius: 6px;
        font-size: 0.9rem;
        cursor: pointer;
        text-decoration: none;
        text-align: center;
        font-weight: 600;
    }
    
    .btn-view {
        background: #f0f0f0;
        color: #333;
    }
    
    .btn-buy {
        background: #667eea;
        color: white;
    }
    
    .btn-buy:hover {
        opacity: 0.9;
    }
    
    @media (max-width: 600px) {
        .modal-content {
            max-width: 95%;
        }
        
        .modal-body {
            padding: 1.5rem 1rem;
        }
    }
`;
document.head.appendChild(style);

// ========== EDIT PRODUCT FUNCTIONS ==========

function openEditModal(productId) {
    fetch(`/api/products/${productId}`)
    .then(r => r.json())
    .then(product => {
        document.getElementById('editProductId').value = product.id;
        document.getElementById('editProductName').value = product.name;
        document.getElementById('editProductPrice').value = product.price;
        document.getElementById('editOriginalPrice').value = product.original_price || '';
        document.getElementById('editProductCategory').value = product.category || '';
        document.getElementById('editProductDesc').value = product.description || '';
        document.getElementById('editProductLink').value = product.affiliate_link || '';
        
        const currentPreview = document.getElementById('editCurrentImagePreview');
        currentPreview.innerHTML = '';
        if (product.images && product.images.length > 0) {
            product.images.forEach((img, i) => {
                const imgEl = document.createElement('img');
                imgEl.src = img;
                imgEl.style.width = '80px';
                imgEl.style.height = '80px';
                imgEl.style.borderRadius = '4px';
                imgEl.style.objectFit = 'cover';
                currentPreview.appendChild(imgEl);
            });
        } else {
            currentPreview.innerHTML = '<small style="color: #999;">No images</small>';
        }
        
        document.querySelector('.edit-images-hidden').value = '[]';
        document.querySelector('.edit-image-preview').innerHTML = '';
        document.getElementById('editProductModal').style.display = 'block';
    })
    .catch(err => alert('❌ Error: ' + err));
}

function closeEditModal() {
    document.getElementById('editProductModal').style.display = 'none';
}

function handleEditLocalImageUpload(event) {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;
    
    const previewDiv = document.querySelector('.edit-image-preview');
    const hiddenInput = document.querySelector('.edit-images-hidden');
    let imageUrls = [];
    
    files.forEach(file => {
        const reader = new FileReader();
        reader.onload = (e) => {
            imageUrls.push(e.target.result);
            
            const img = document.createElement('img');
            img.src = e.target.result;
            img.style.width = '80px';
            img.style.height = '80px';
            img.style.margin = '5px';
            img.style.borderRadius = '4px';
            img.style.objectFit = 'cover';
            previewDiv.appendChild(img);
            
            if (imageUrls.length === files.length) {
                hiddenInput.value = JSON.stringify(imageUrls);
            }
        };
        reader.readAsDataURL(file);
    });
}

async function updateProduct(event) {
    event.preventDefault();
    
    const productId = document.getElementById('editProductId').value;
    const formData = new FormData();
    
    formData.append('name', document.getElementById('editProductName').value);
    formData.append('price', document.getElementById('editProductPrice').value);
    formData.append('affiliate_link', document.getElementById('editProductLink').value);
    formData.append('category', document.getElementById('editProductCategory').value);
    formData.append('description', document.getElementById('editProductDesc').value);
    formData.append('original_price', document.getElementById('editOriginalPrice').value || '');
    
    const newImagesHidden = document.querySelector('.edit-images-hidden');
    let newImages = [];
    try {
        newImages = JSON.parse(newImagesHidden.value || '[]');
    } catch (e) {}
    
    if (newImages.length > 0) {
        formData.append('images_json', JSON.stringify(newImages));
    }
    
    try {
        const response = await fetch(`/api/products/${productId}`, {
            method: 'PUT',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert('✅ Product updated!');
            closeEditModal();
            loadProducts();
        } else {
            alert('❌ Error: ' + result.error);
        }
    } catch (error) {
        alert('❌ Error: ' + error.message);
    }
}

// ========== LOAD PRODUCTS IN ADMIN DASHBOARD ==========

async function loadAdminProducts() {
    try {
        const grid = document.getElementById('adminProductsGrid');
        if (!grid) return;
        
        const response = await fetch('/api/products');
        const products = await response.json();
        
        if (!Array.isArray(products) || products.length === 0) {
            grid.innerHTML = '<div class="loading">No products yet. Add one above! ⬆️</div>';
            return;
        }
        
        grid.innerHTML = products.map(p => {
            const images = p.images && p.images.length > 0 ? p.images : ['https://via.placeholder.com/300x200?text=No+Image'];
            const imageUrl = images[0].startsWith('data:') || images[0].startsWith('http') 
                ? images[0] 
                : (images[0].startsWith('/') ? images[0] : '/uploads/' + images[0]);
            
            return `
                <div class="product-card">
                    <img src="${imageUrl}" alt="${p.name}" class="product-image" 
                         onerror="this.src='https://via.placeholder.com/300x200?text=No+Image'">
                    <h3>${p.name}</h3>
                    <p class="price">₹${p.price}</p>
                    ${p.original_price ? `<p class="original-price" style="text-decoration: line-through; color: #999;">₹${p.original_price}</p>` : ''}
                    <p class="category">${p.category}</p>
                    <div class="product-actions">
                        <button class="btn-view" onclick="event.stopPropagation(); editProductQuick('${p.id}')">✏️ Edit</button>
                        <button class="btn-view" onclick="event.stopPropagation(); deleteProduct('${p.id}')">🗑️ Delete</button>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading admin products:', error);
    }
}

function editProductQuick(productId) {
    document.getElementById('editProductId').value = productId;
    loadProductForEdit();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function deleteProduct(productId) {
    if (!confirm('Are you sure? This cannot be undone!')) return;
    
    try {
        const response = await fetch(`/api/products/${productId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            alert('✅ Product deleted!');
            loadAdminProducts();
        } else {
            alert('❌ Error deleting product');
        }
    } catch (error) {
        alert('❌ Error: ' + error.message);
    }
}
