async function loadAdminProducts() {
    console.log('loadAdminProducts called');
    const grid = document.getElementById('adminProductsGrid');
    
    if (!grid) {
        console.error('Grid not found');
        return;
    }
    
    try {
        const response = await fetch('/api/products');
        console.log('Response:', response.status);
        
        if (!response.ok) {
            grid.innerHTML = `<p>Error: ${response.status}</p>`;
            return;
        }
        
        const products = await response.json();
        console.log('Products:', products);
        
        if (!products || products.length === 0) {
            grid.innerHTML = '<p>No products yet</p>';
            return;
        }
        
        let html = '';
        products.forEach(p => {
            const img = p.images && p.images[0] ? p.images[0] : 'https://via.placeholder.com/200';
            html += `
                <div style="border: 1px solid #ddd; padding: 1rem; border-radius: 8px; text-align: center;">
                    <img src="${img}" style="width: 100%; height: 150px; object-fit: cover; border-radius: 4px;" onerror="this.src='https://via.placeholder.com/200'">
                    <h4>${p.name}</h4>
                    <p>₹${p.price}</p>
                    <button onclick="editProductQuick('${p.id}')" style="background: #3498db; color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer;">✏️ Edit</button>
                    <button onclick="deleteProduct('${p.id}')" style="background: #e74c3c; color: white; border: none; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; margin-left: 0.5rem;">🗑️ Delete</button>
                </div>
            `;
        });
        
        grid.innerHTML = html;
    } catch (error) {
        console.error('Error:', error);
        grid.innerHTML = `<p>Error: ${error.message}</p>`;
    }
}
