async function loadProducts(category = 'all') {
    const grid = document.getElementById('productsGrid');
    grid.innerHTML = '<div class="loading">Loading deals... 🛍️</div>';
    
    try {
        const url = category === 'all' ? '/api/products' : `/api/products?category=${category}`;
        const res = await fetch(url);
        const products = await res.json();
        
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
    
    return `
        <article class="product-card">
            ${dealBadge ? `<span class="deal-badge">${dealBadge}</span>` : ''}
            <img src="${imageUrl}" alt="${p.name}" class="product-image" 
                 onerror="this.src='https://via.placeholder.com/300x200?text=No+Image'">
            <div class="product-info">
                <span class="category">${p.category}</span>
                <h3>${p.name}</h3>
                <div class="price-section">
                    <span class="price">${p.price}</span>
                    ${p.original_price ? `<span class="original-price">${p.original_price}</span>` : ''}
                    ${discount ? `<span class="discount">(${discount}% OFF)</span>` : ''}
                </div>
                ${p.description ? `<p class="description">${p.description}</p>` : ''}
                <a href="/go/${p.id}" target="_blank" rel="noopener noreferrer" class="buy-btn">
                    🛒 Buy Now →
                </a>
            </div>
        </article>
    `;
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
            <a href="/go/${deal.id}" target="_blank" class="buy-btn" style="padding:0.4rem 1rem; font-size:0.9rem; margin-top:0.5rem; display:inline-block; width:auto;">
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
