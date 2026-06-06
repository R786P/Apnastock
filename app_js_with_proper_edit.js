// ========== EDIT PRODUCT FUNCTIONS ==========

function editProductQuick(productId) {
    console.log('Editing product:', productId);
    
    // Fetch product data
    fetch(`/api/products/${productId}`)
    .then(r => r.json())
    .then(product => {
        console.log('Loaded product:', product);
        
        // Populate form
        document.getElementById('productName').value = product.name;
        document.getElementById('productPrice').value = product.price;
        document.getElementById('originalPrice').value = product.original_price || '';
        document.getElementById('productCategory').value = product.category || '';
        document.getElementById('productDesc').value = product.description || '';
        document.getElementById('productLink').value = product.affiliate_link || '';
        document.getElementById('editProductId').value = productId;
        
        // Show images
        const preview = document.querySelector('.image-preview');
        preview.innerHTML = '';
        if (product.images && product.images.length > 0) {
            product.images.forEach(img => {
                const imgEl = document.createElement('img');
                imgEl.src = img;
                imgEl.style.width = '80px';
                imgEl.style.height = '80px';
                imgEl.style.margin = '5px';
                imgEl.style.borderRadius = '4px';
                imgEl.style.objectFit = 'cover';
                preview.appendChild(imgEl);
            });
        }
        
        // Scroll to form
        document.getElementById('productForm').scrollIntoView({ behavior: 'smooth' });
        
        // Highlight form
        document.getElementById('productForm').style.border = '3px solid #3498db';
        setTimeout(() => {
            document.getElementById('productForm').style.border = 'none';
        }, 3000);
        
        alert('✅ Product loaded! Now edit and click Update!');
    })
    .catch(err => {
        console.error('Error:', err);
        alert('❌ Error loading product: ' + err.message);
    });
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
    
    if (!productId) {
        alert('❌ No product selected to edit!');
        return;
    }
    
    const formData = new FormData();
    
    formData.append('name', document.getElementById('productName').value);
    formData.append('price', document.getElementById('productPrice').value);
    formData.append('affiliate_link', document.getElementById('productLink').value);
    formData.append('category', document.getElementById('productCategory').value);
    formData.append('description', document.getElementById('productDesc').value);
    formData.append('original_price', document.getElementById('originalPrice').value || '');
    
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
            alert('✅ Product updated successfully!');
            
            // Reset form
            document.getElementById('productForm').reset();
            document.getElementById('editProductId').value = '';
            document.querySelector('.image-preview').innerHTML = '';
            document.querySelector('.edit-images-hidden').value = '[]';
            document.querySelector('.edit-image-preview').innerHTML = '';
            
            // Reload products list
            loadAdminProducts();
        } else {
            alert('❌ Error: ' + result.error);
        }
    } catch (error) {
        alert('❌ Error: ' + error.message);
    }
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
