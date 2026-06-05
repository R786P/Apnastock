// ========== IMAGE UPLOAD WITH MULTIPLE OPTIONS ==========

// Handle Local File Upload
async function handleLocalImageUpload(event) {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;
    
    const container = event.target.closest('.image-upload-section');
    const previewDiv = container.querySelector('.image-preview');
    const hiddenInput = container.querySelector('.images-hidden');
    
    let imageUrls = [];
    
    // Convert files to base64 data URLs
    for (let file of files) {
        const reader = new FileReader();
        reader.onload = (e) => {
            imageUrls.push(e.target.result);
            
            // Update preview
            const img = document.createElement('img');
            img.src = e.target.result;
            img.style.width = '80px';
            img.style.height = '80px';
            img.style.margin = '5px';
            img.style.borderRadius = '4px';
            img.style.objectFit = 'cover';
            previewDiv.appendChild(img);
            
            // Update hidden input when all files loaded
            if (imageUrls.length === files.length) {
                hiddenInput.value = JSON.stringify(imageUrls);
            }
        };
        reader.readAsDataURL(file);
    }
}

// Handle Google Drive URL
function handleGoogleDriveUrl(event) {
    const container = event.target.closest('.image-upload-section');
    const urlInput = container.querySelector('.drive-url-input');
    const url = urlInput.value.trim();
    const previewDiv = container.querySelector('.image-preview');
    const hiddenInput = container.querySelector('.images-hidden');
    
    if (!url) {
        alert('Please enter a valid Google Drive URL');
        return;
    }
    
    // Extract file ID from Google Drive URL
    let fileId = null;
    
    // Format 1: https://drive.google.com/file/d/FILE_ID/view
    const match1 = url.match(/\/d\/([a-zA-Z0-9-_]+)/);
    if (match1) fileId = match1[1];
    
    // Format 2: https://drive.google.com/open?id=FILE_ID
    const match2 = url.match(/id=([a-zA-Z0-9-_]+)/);
    if (match2) fileId = match2[1];
    
    if (!fileId) {
        alert('Invalid Google Drive URL format. Please use:\nhttps://drive.google.com/file/d/FILE_ID/view');
        return;
    }
    
    // Create direct image URL from Google Drive
    const imageUrl = `https://drive.google.com/uc?export=view&id=${fileId}`;
    
    // Add to preview
    const img = document.createElement('img');
    img.src = imageUrl;
    img.style.width = '80px';
    img.style.height = '80px';
    img.style.margin = '5px';
    img.style.borderRadius = '4px';
    img.style.objectFit = 'cover';
    img.onerror = () => {
        alert('Failed to load image from Google Drive. Make sure the link is publicly accessible.');
        img.remove();
    };
    previewDiv.appendChild(img);
    
    // Add to hidden input
    let currentImages = [];
    try {
        currentImages = JSON.parse(hiddenInput.value || '[]');
    } catch (e) {
        currentImages = [];
    }
    currentImages.push(imageUrl);
    hiddenInput.value = JSON.stringify(currentImages);
    
    // Clear input
    urlInput.value = '';
}

// Clear all images
function clearAllImages(event) {
    const container = event.target.closest('.image-upload-section');
    const previewDiv = container.querySelector('.image-preview');
    const hiddenInput = container.querySelector('.images-hidden');
    const fileInput = container.querySelector('.local-file-input');
    const urlInput = container.querySelector('.drive-url-input');
    
    previewDiv.innerHTML = '';
    hiddenInput.value = '';
    fileInput.value = '';
    urlInput.value = '';
}

// Remove specific image
function removeImage(index, container) {
    const hiddenInput = container.querySelector('.images-hidden');
    let images = JSON.parse(hiddenInput.value || '[]');
    images.splice(index, 1);
    hiddenInput.value = JSON.stringify(images);
    
    // Refresh preview
    const previewDiv = container.querySelector('.image-preview');
    previewDiv.innerHTML = '';
    images.forEach((img, i) => {
        const imgEl = document.createElement('img');
        imgEl.src = img;
        imgEl.style.width = '80px';
        imgEl.style.height = '80px';
        imgEl.style.margin = '5px';
        imgEl.style.borderRadius = '4px';
        imgEl.style.objectFit = 'cover';
        imgEl.style.position = 'relative';
        imgEl.style.cursor = 'pointer';
        
        const removeBtn = document.createElement('button');
        removeBtn.innerHTML = '✕';
        removeBtn.style.position = 'absolute';
        removeBtn.style.top = '0';
        removeBtn.style.right = '0';
        removeBtn.style.background = '#e74c3c';
        removeBtn.style.color = 'white';
        removeBtn.style.border = 'none';
        removeBtn.style.borderRadius = '50%';
        removeBtn.style.width = '20px';
        removeBtn.style.height = '20px';
        removeBtn.style.cursor = 'pointer';
        removeBtn.style.fontSize = '12px';
        removeBtn.onclick = () => removeImage(i, container);
        
        const wrapper = document.createElement('div');
        wrapper.style.position = 'relative';
        wrapper.style.display = 'inline-block';
        wrapper.appendChild(imgEl);
        wrapper.appendChild(removeBtn);
        previewDiv.appendChild(wrapper);
    });
}
