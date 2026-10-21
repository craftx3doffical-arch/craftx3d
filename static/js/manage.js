// ═══════════════════════════════════════════════════════
//  CRAFTIX 3D — Staff Portal JS
// ═══════════════════════════════════════════════════════

const CSRF = document.cookie.split('; ').find(r => r.startsWith('csrftoken='))?.split('=')[1] || '';

// ─── TOAST ────────────────────────────────────────────
function showMToast(message, type = 'info', duration = 3500) {
  const container = document.getElementById('mToastContainer');
  if (!container) return;

  const colors = { success: '#1A9B77', error: '#D9534F', info: '#F5A623' };
  const icons  = { success: '✅', error: '❌', info: 'ℹ️' };

  const toast = document.createElement('div');
  toast.style.cssText = `
    background:#1A1A2E;color:#fff;padding:12px 18px;border-radius:10px;
    font-size:0.82rem;box-shadow:0 4px 20px rgba(0,0,0,0.25);
    display:flex;align-items:center;gap:10px;
    border-left:4px solid ${colors[type] || colors.info};
    min-width:260px;animation:slideInToast 0.3s ease;
  `;
  toast.innerHTML = `<span>${icons[type]}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = 'opacity 0.3s, transform 0.3s';
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ─── CSRF FETCH ───────────────────────────────────────
async function mFetch(url, data = {}) {
  const body = new URLSearchParams(data);
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'X-CSRFToken': CSRF, 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString()
  });
  return res.json();
}

// ─── MODAL MANAGEMENT ─────────────────────────────────
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add('show');
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove('show');
}

// Close modals on backdrop click
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.m-modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', e => {
      if (e.target === overlay) overlay.classList.remove('show');
    });
  });

  // Close on Escape
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.m-modal-overlay.show').forEach(m => m.classList.remove('show'));
    }
  });
});

// ─── TOGGLE STATUS HELPERS ────────────────────────────
async function toggleProduct(pk, el) {
  try {
    const data = await mFetch(`/manage/products/${pk}/toggle/`);
    showMToast(data.is_active ? 'Product activated' : 'Product deactivated', 'success');
    // Sync checkboxes
    if (el && el.type === 'checkbox') el.checked = data.is_active;
  } catch(e) {
    showMToast('Error updating product', 'error');
  }
}

async function updateOrderStatus(orderId, status) {
  try {
    const data = await mFetch(`/manage/orders/${orderId}/status/`, { status });
    if (data.success) showMToast(`Order status updated to ${status}`, 'success');
    else showMToast('Error updating order', 'error');
  } catch(e) {
    showMToast('Error updating order', 'error');
  }
}

async function updateEnquiryStatus(pk, status) {
  await mFetch(`/manage/enquiries/${pk}/status/`, { status });
  showMToast('Status updated', 'success');
}

// ─── IMAGE PREVIEW ────────────────────────────────────
function previewNewImages(input) {
  const grid = document.getElementById('imgGrid');
  if (!grid) return;
  Array.from(input.files).forEach(file => {
    const url = URL.createObjectURL(file);
    const slot = document.createElement('div');
    slot.className = 'img-slot has-image';
    slot.innerHTML = `<img src="${url}" style="width:100%;height:100%;object-fit:cover;" alt=""><button type="button" class="img-slot-remove" onclick="this.parentElement.remove()">✕</button>`;
    grid.insertBefore(slot, grid.lastElementChild);
  });
}

async function removeProductImage(pk, containerEl) {
  try {
    const data = await mFetch(`/manage/products/image/${pk}/delete/`);
    if (data.success) {
      containerEl?.remove();
      showMToast('Image removed', 'info');
    }
  } catch(e) {
    showMToast('Error removing image', 'error');
  }
}

// ─── CONFIRM DELETE MODAL ─────────────────────────────
function confirmDelete(url, name, modalId = 'deleteModal') {
  const modal = document.getElementById(modalId);
  const target = document.getElementById('deleteTarget');
  const form = document.getElementById('deleteForm');
  if (!modal || !form) return;
  if (target) target.textContent = name;
  form.action = url;
  modal.classList.add('show');
}

function closeDeleteModal(modalId = 'deleteModal') {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('show');
}

// ─── INVENTORY INLINE SAVE ────────────────────────────
async function saveInventory(pk) {
  const priceEl = document.getElementById(`price-${pk}`);
  const stockEl = document.getElementById(`stock-${pk}`);
  if (!priceEl || !stockEl) return;

  try {
    const data = await mFetch(`/manage/inventory/${pk}/update/`, {
      price: priceEl.value,
      stock: stockEl.value
    });
    if (data.success) {
      const saveEl = document.getElementById(`save-${pk}`);
      if (saveEl) {
        saveEl.style.display = 'inline';
        setTimeout(() => { saveEl.style.display = 'none'; }, 2000);
      }
    }
  } catch(e) {
    showMToast('Error saving', 'error');
  }
}

// ─── REVIEW ACTIONS ───────────────────────────────────
function reviewAction(pk, action) {
  const form = document.createElement('form');
  form.method = 'POST';
  form.action = `/manage/reviews/${pk}/${action}/`;
  form.innerHTML = `<input name="csrfmiddlewaretoken" value="${CSRF}">`;
  document.body.appendChild(form);
  form.submit();
}

// ─── TOPBAR SEARCH ────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.querySelector('.topbar-search-input');
  if (searchInput) {
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        // Could implement live search here
      }, 400);
    });

    searchInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        const q = searchInput.value.trim();
        if (q) window.location.href = `/manage/products/?q=${encodeURIComponent(q)}`;
      }
    });
  }
});

// ─── COUPON CODE UPPERCASE ────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[name="code"]').forEach(input => {
    input.addEventListener('input', () => { input.value = input.value.toUpperCase(); });
  });
});
