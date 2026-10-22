// ═══════════════════════════════════════════════════════
//  CRAFTIX 3D — Customer Portal JS  (v2)
// ═══════════════════════════════════════════════════════
'use strict';

const CSRF = () => document.cookie.split('; ').find(r => r.startsWith('csrftoken='))?.split('=')[1] || '';

// ── TOAST ─────────────────────────────────────────────
function showToast(msg, type, dur) {
  type = type || 'info'; dur = dur || 3500;
  let box = document.getElementById('toastContainer');
  if (!box) { box = document.createElement('div'); box.id = 'toastContainer'; box.className = 'toast-container'; document.body.appendChild(box); }
  var icons = { success:'✅', error:'❌', info:'ℹ️', cart:'🛒' };
  var t = document.createElement('div');
  t.className = 'toast ' + type;
  t.innerHTML = '<span>' + (icons[type]||'ℹ️') + '</span><span>' + msg + '</span>';
  box.appendChild(t);
  setTimeout(function() { t.style.cssText += 'opacity:0;transform:translateX(20px);transition:all 0.4s'; setTimeout(function(){t.remove();},400); }, dur);
}

// ── CART POPUP ────────────────────────────────────────
function showCartPopup(data) {
  var popup = document.getElementById('cartAddedPopup');
  if (!popup) {
    popup = document.createElement('div');
    popup.id = 'cartAddedPopup';
    popup.innerHTML = '<div class="cap-inner"><div class="cap-header"><span class="cap-title">🛒 Added to Cart!</span><button class="cap-close" onclick="document.getElementById(\'cartAddedPopup\').classList.remove(\'show\')">✕</button></div><div class="cap-product" id="capProduct"></div><div class="cap-totals" id="capTotals"></div><div class="cap-actions"><a href="/cart/" class="cap-btn-primary">View Cart</a><button class="cap-btn-ghost" onclick="document.getElementById(\'cartAddedPopup\').classList.remove(\'show\')">Continue Shopping</button></div></div>';
    document.body.appendChild(popup);
    var s = document.createElement('style');
    s.textContent = '#cartAddedPopup{position:fixed;inset:0;z-index:8000;display:flex;align-items:center;justify-content:center;padding:16px;background:rgba(0,0,0,0.45);opacity:0;pointer-events:none;transition:opacity 0.3s}#cartAddedPopup.show{opacity:1;pointer-events:all}.cap-inner{background:#fff;border-radius:20px;padding:28px;max-width:400px;width:100%;box-shadow:0 20px 60px rgba(0,0,0,0.2);transform:translateY(16px);transition:transform 0.3s}#cartAddedPopup.show .cap-inner{transform:translateY(0)}.cap-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px}.cap-title{font-weight:800;font-size:1.05rem}.cap-close{background:none;border:none;font-size:1.2rem;cursor:pointer;color:#999;padding:4px}.cap-product{display:flex;gap:14px;align-items:center;padding:14px;background:#ffffff;border:1px solid #e4e4e4;border-radius:12px;margin-bottom:14px}.cap-product img{width:64px;height:64px;object-fit:contain;border-radius:8px;background:#fff;padding:4px}.cap-product-name{font-weight:700;font-size:0.95rem;margin-bottom:3px}.cap-product-price{color:#6B6B6B;font-size:0.85rem}.cap-totals{display:flex;justify-content:space-between;font-size:0.88rem;color:#6B6B6B;margin-bottom:18px}.cap-actions{display:flex;gap:10px;flex-direction:column}.cap-btn-primary{display:block;text-align:center;padding:13px;background:#1C1C1E;color:#fff;border-radius:10px;font-weight:700;text-decoration:none}.cap-btn-ghost{background:none;border:1.5px solid #E8E0CC;border-radius:10px;padding:11px;font-weight:600;cursor:pointer;font-family:inherit;font-size:0.9rem}';
    document.head.appendChild(s);
  }
  var img = data.image_url ? '<img src="'+data.image_url+'" alt="">' : '<div style="width:64px;height:64px;background:#eee;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1.8rem">📦</div>';
  document.getElementById('capProduct').innerHTML = img + '<div><div class="cap-product-name">'+data.product_name+'</div><div class="cap-product-price">₹'+parseFloat(data.product_price).toFixed(2)+'</div></div>';
  document.getElementById('capTotals').innerHTML = '<span>Cart subtotal</span><strong>₹'+parseFloat(data.cart_subtotal).toFixed(2)+'</strong>';
  popup.classList.add('show');
  updateCartBadge(data.cart_count);
}

// ── CART BADGE ────────────────────────────────────────
function updateCartBadge(count) {
  var badge = document.querySelector('.cart-badge');
  var btn = document.querySelector('.btn-cart');
  if (!btn) return;
  if (!badge) { badge = document.createElement('span'); badge.className = 'cart-badge'; btn.appendChild(badge); }
  badge.textContent = count; badge.style.display = count > 0 ? 'flex' : 'none';
}

// ── AJAX ADD TO CART — comprehensive version with inline field validation ──
function initAddToCart() {
  var form = document.getElementById('addToCartForm');
  if (!form) return;
  var addBtn = document.getElementById('addCartBtn') || form.querySelector('[type="submit"]');

  // ── Helpers ──────────────────────────────────────────────────────────────
  function isFieldValid(f) {
    if (f.type === 'file') return !!(f.files && f.files.length > 0);
    if (f.type === 'radio') return true; // radio groups validated separately
    return f.value.trim() !== '';
  }

  function errEl(f) { return f.id ? document.getElementById('err_' + f.id) : null; }
  function zoneEl(f) { return f.id ? document.getElementById(f.id + '_zone') : null; } // photo upload label wrapper

  function showFieldError(f) {
    var err = errEl(f); if (err) err.classList.add('show');
    f.classList.add('field-invalid');
    var z = zoneEl(f); if (z) z.classList.add('field-invalid');
  }
  function clearFieldError(f) {
    var err = errEl(f); if (err) err.classList.remove('show');
    f.classList.remove('field-invalid');
    var z = zoneEl(f); if (z) z.classList.remove('field-invalid');
  }

  // ── Required-field checker — drives both the button state AND inline errors ──
  function checkRequired(opts) {
    opts = opts || {};
    var allRequired = Array.from(form.querySelectorAll('[required]'));
    var radioGroups = {};
    var ok = true;

    allRequired.forEach(function(f) {
      if (f.type === 'radio') {
        radioGroups[f.name] = radioGroups[f.name] || [];
        radioGroups[f.name].push(f);
        return;
      }
      var valid = isFieldValid(f);
      if (!valid) ok = false;
      // Only reveal an inline error once the customer has touched that field,
      // or when we're forcing every error visible (a real submit attempt).
      if (opts.forceShowAll || f.dataset.touched === '1') {
        if (valid) clearFieldError(f); else showFieldError(f);
      }
    });

    var radioOk = Object.keys(radioGroups).every(function(name) {
      return form.querySelector('input[type="radio"][name="' + name + '"]:checked');
    });
    if (!radioOk) ok = false;

    if (addBtn) {
      addBtn.classList.toggle('btn-locked', !ok);
      addBtn.title = ok ? '' : 'Please complete the customization fields above first';
    }
    return ok;
  }
  // Expose globally so dynamically-toggled required fields (e.g. personalisation
  // text becoming required when the customer selects "Yes") can trigger an
  // immediate re-check instead of waiting for the next input/change event.
  window._recheckAddToCartGate = checkRequired;

  function markTouchedAndCheck(f) { f.dataset.touched = '1'; checkRequired(); }

  // Listen on fields — guarded so repeated re-renders never double-bind the
  // same element (which previously caused listener counts to grow unbounded).
  function attachListeners() {
    form.querySelectorAll('input, textarea, select').forEach(function(f) {
      if (f.dataset.gateBound === '1') return;
      f.dataset.gateBound = '1';
      f.addEventListener('input', function() { checkRequired(); });
      f.addEventListener('change', function() { markTouchedAndCheck(f); });
      f.addEventListener('blur', function() { markTouchedAndCheck(f); });
    });
  }
  attachListeners();

  // Re-check after the customization renderer adds dynamic fields
  var _recheckTimer = null;
  function scheduleRecheck() {
    clearTimeout(_recheckTimer);
    _recheckTimer = setTimeout(function() { attachListeners(); checkRequired(); }, 150);
  }
  var cfContainer = document.getElementById('customizationFields');
  if (cfContainer && window.MutationObserver) {
    new MutationObserver(scheduleRecheck).observe(cfContainer, { childList: true, subtree: true });
  }
  setTimeout(function() { attachListeners(); checkRequired(); }, 600);

  // ── Form submit ──
  form.addEventListener('submit', function(e) {
    e.preventDefault();

    // 1. Validate ALL required customization fields, revealing every error at once
    if (!checkRequired({ forceShowAll: true })) {
      var firstEmpty = Array.from(form.querySelectorAll('[required]')).find(function(f) {
        if (f.type === 'radio') return false;
        return !isFieldValid(f);
      });
      if (firstEmpty) {
        var scrollTarget = zoneEl(firstEmpty) || firstEmpty;
        scrollTarget.scrollIntoView({ behavior: 'smooth', block: 'center' });
        if (typeof firstEmpty.focus === 'function' && firstEmpty.type !== 'file') firstEmpty.focus();
      }
      showToast('⚠️ Please fill the required field(s) highlighted below before adding to cart.', 'error');
      return;
    }

    // 2. Stock quantity check (client-side)
    var qtyInput = document.getElementById('qty');
    if (qtyInput) {
      var qty = parseInt(qtyInput.value) || 1;
      var maxQty = parseInt(qtyInput.getAttribute('max') || '9999');
      if (qty > maxQty) {
        showToast('⚠️ Only ' + maxQty + ' item(s) in stock. Please reduce quantity.', 'error');
        qtyInput.value = maxQty;
        qtyInput.focus();
        return;
      }
      if (qty < 1) {
        qtyInput.value = 1;
        return;
      }
    }

    // 3. Submit via AJAX
    syncSizePrice();
    if (addBtn) { addBtn.classList.add('btn-locked'); addBtn.textContent = 'Adding…'; }
    var formData = new FormData(form);

    // Include dynamically created customization file inputs
    document.querySelectorAll('#customizationFields input[type="file"]').forEach(function(inp) {
      if (inp.files && inp.files.length > 0) {
        for (var i = 0; i < inp.files.length; i++) {
          if (!formData.has(inp.name)) formData.append(inp.name, inp.files[i]);
        }
      }
    });

    fetch(form.action, {
      method: 'POST',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      body: formData
    }).then(function(r) {
      if (r.status === 401) {
        return r.json().then(function(d) {
          window.location.href = d.redirect || '/accounts/login/';
        });
      }
      return r.json().then(function(data) {
        if (addBtn) { addBtn.innerHTML = '🛒 Add to Cart'; checkRequired(); }
        if (data.success) {
          var badge = document.getElementById('cartBadgeNav');
          if (badge) { badge.textContent = data.cart_count; badge.style.display = 'flex'; }
          var countLabel = document.getElementById('cartCountLabel');
          if (countLabel) countLabel.textContent = data.cart_count;
          showToast('Added to cart!', 'success');
          // Just add it — stay exactly where the customer is. Don't open the
          // drawer or navigate anywhere. Refresh the drawer's contents silently
          // in the background so it's up to date when they choose to open it.
          if (typeof refreshCartDrawer === 'function') refreshCartDrawer();
          // Clear the customization the customer just added (uploaded photo
          // previews, text fields, chosen options) so it doesn't linger on the
          // page looking like it's still pending — it's now safely in the cart.
          if (typeof resetCustomizationForm === 'function') resetCustomizationForm(form);
        } else if (data.error === 'out_of_stock') {
          showToast('❌ ' + (data.message || 'Out of stock'), 'error');
          // Update max on qty input
          if (qtyInput) { qtyInput.max = 0; qtyInput.value = 0; }
        } else if (data.need_login) {
          window.location.href = data.redirect || '/accounts/login/';
        } else {
          showToast('❌ ' + (data.message || 'Could not add to cart'), 'error');
        }
      });
    }).catch(function() {
      // Do NOT fall back to a native form.submit() here — that navigates the
      // browser to the cart page (a plain POST response), which is exactly the
      // "add to cart jumps to the cart page" behaviour reported on mobile when
      // the network hiccups. Instead, re-enable the button and let them retry.
      if (addBtn) { addBtn.classList.remove('btn-locked'); addBtn.innerHTML = '🛒 Add to Cart'; }
      showToast('⚠️ Network issue — please tap Add to Cart again.', 'error');
    });
  });
}

// ── INTERACTIVE STAR RATING ───────────────────────────
function initStarRating() {
  var container = document.getElementById('starRating');
  if (!container) return;
  var stars = Array.from(container.querySelectorAll('.star-btn'));
  var hiddenInput = document.getElementById('ratingValue');
  var selected = parseInt(hiddenInput ? hiddenInput.value : 0) || 0;
  var labels = ['','Poor','Fair','Good','Great','Excellent!'];

  function paint(val) {
    stars.forEach(function(s,i){ s.textContent = i < val ? '★' : '☆'; s.style.color = i < val ? '#FFB800' : '#ccc'; });
  }
  stars.forEach(function(star, i) {
    star.addEventListener('mouseenter', function(){ paint(i+1); });
    star.addEventListener('mouseleave', function(){ paint(selected); });
    star.addEventListener('click', function(){
      selected = i+1;
      if (hiddenInput) hiddenInput.value = selected;
      paint(selected);
      var lbl = document.getElementById('ratingLabel');
      if (lbl) { lbl.textContent = labels[selected]; lbl.style.opacity='1'; }
    });
  });
  paint(selected);
}

// ── HELP FORM VALIDATION ──────────────────────────────
function initHelpForm() {
  var form = document.getElementById('helpForm');
  var btn = document.getElementById('helpSubmitBtn');
  if (!form || !btn) return;
  function check() {
    var ok = Array.from(form.querySelectorAll('[required]')).every(function(f){ return f.value.trim() !== ''; });
    btn.disabled = !ok; btn.style.opacity = ok ? '1' : '0.45'; btn.style.cursor = ok ? 'pointer' : 'not-allowed';
  }
  form.querySelectorAll('input,textarea,select').forEach(function(f){ f.addEventListener('input', check); });
  check();
  // Prevent multiple submissions — disable button immediately on first valid submit
  var _submitting = false;
  form.addEventListener('submit', function(e) {
    if (_submitting) { e.preventDefault(); return; }
    _submitting = true;
    btn.disabled = true;
    btn.textContent = 'Sending…';
    btn.style.opacity = '0.65';
    btn.style.cursor = 'not-allowed';
  });
}

// ── FAQ ACCORDION ─────────────────────────────────────
function initFaqs() {
  document.querySelectorAll('.faq-question').forEach(function(btn) {
    btn.addEventListener('click', function(){
      var item = btn.closest('.faq-item');
      var isOpen = item.classList.contains('open');
      document.querySelectorAll('.faq-item.open').forEach(function(i){ i.classList.remove('open'); });
      if (!isOpen) item.classList.add('open');
    });
  });
}

// ── CART UPDATE ───────────────────────────────────────
function updateCart(itemId, action) {
  fetch('/cart/update/'+itemId+'/', { method:'POST', headers:{'X-CSRFToken':CSRF(),'X-Requested-With':'XMLHttpRequest','Content-Type':'application/x-www-form-urlencoded'}, body:'action='+action })
    .then(function(r){ return r.json(); })
    .then(function(data) {
      if (!data.success) return;
      if (action === 'remove') {
        var el = document.getElementById('cart-item-'+itemId);
        if (el) { el.style.cssText += 'opacity:0;transition:opacity 0.3s'; setTimeout(function(){ el.remove(); }, 300); }
        showToast('Item removed','info');
      } else {
        var q = document.getElementById('qty-'+itemId); var t = document.getElementById('item-total-'+itemId);
        if(q) q.textContent = data.quantity; if(t) t.textContent = '₹'+parseFloat(data.item_total).toFixed(2);
      }
      var sub = document.getElementById('cart-subtotal'); var tot = document.getElementById('cart-total');
      if(sub) sub.textContent = '₹'+parseFloat(data.cart_subtotal).toFixed(2);
      if(tot) tot.textContent = '₹'+parseFloat(data.cart_total).toFixed(2);
      var parcelRow = document.getElementById('parcelChargeRow'); var parcelEl = document.getElementById('cart-parcel-charge');
      if(parcelEl) parcelEl.textContent = '₹'+parseFloat(data.cart_parcel_charge || 0).toFixed(2);
      if(parcelRow) parcelRow.style.display = (data.cart_parcel_charge > 0) ? '' : 'none';
      updateCartBadge(data.cart_count);
    });
}

function toggleCouponInput() {
  var s = document.getElementById('couponInputSection');
  if (!s) return;
  var isOpen = s.getAttribute('data-open') === 'true';
  s.setAttribute('data-open', isOpen ? 'false' : 'true');
  s.style.display = isOpen ? 'none' : 'block';
  var arrow = document.getElementById('couponArrow');
  if (arrow) arrow.style.transform = isOpen ? 'rotate(0deg)' : 'rotate(180deg)';
}

function applyCoupon() {
  var code = (document.getElementById('couponCode')||{}).value; if(!code) return;
  fetch('/cart/coupon/', {method:'POST',headers:{'X-CSRFToken':CSRF(),'Content-Type':'application/x-www-form-urlencoded'},body:'coupon_code='+encodeURIComponent(code.trim().toUpperCase())})
    .then(function(r){return r.json();}).then(function(data){
      var msg = document.getElementById('couponMessage');
      if(msg){ msg.textContent=data.message; msg.style.color=data.success?'var(--teal)':'var(--red)'; }
      if(data.success){ var t=document.getElementById('cart-total'); if(t) t.textContent='₹'+parseFloat(data.total).toFixed(2); }
      showToast(data.message, data.success?'success':'error');
    });
}

var _giftWrapBusy = false;
function toggleGiftWrap() {
  var cb = document.getElementById('giftWrap');
  if (_giftWrapBusy) { if (cb) cb.checked = !cb.checked; return; } // revert visual if busy
  _giftWrapBusy = true;
  fetch('/cart/gift-wrap/',{method:'POST',headers:{'X-CSRFToken':CSRF()}})
    .then(function(r){return r.json();})
    .then(function(data){
      // Sync checkbox to actual server state — prevents visual/state mismatch
      if (cb) cb.checked = !!data.gift_wrap;
      var t=document.getElementById('cart-total');
      if(t&&data.total!==undefined) t.textContent='₹'+parseFloat(data.total).toFixed(2);
    })
    .catch(function(){ if(cb) cb.checked=!cb.checked; }) // revert on error
    .finally(function(){ _giftWrapBusy=false; });
}

// ── PRODUCT GALLERY ───────────────────────────────────
function switchImage(url, el) {
  var main = document.getElementById('mainImg');
  if(main){ main.style.opacity='0.5'; main.src=url; main.onload=function(){ main.style.opacity='1'; }; }
  document.querySelectorAll('.product-thumb').forEach(function(t){ t.classList.remove('active'); });
  if(el) el.classList.add('active');
}
function changeQty(d) {
  var inp = document.getElementById('qty'); if(!inp) return;
  inp.value = Math.max(1, Math.min(parseInt(inp.value||1)+d, parseInt(inp.max)||99));
}
function toggleAccord(id) {
  var item = document.getElementById(id); if(!item) return;
  var isOpen = item.classList.contains('open');
  document.querySelectorAll('.accordion-item.open').forEach(function(i){ i.classList.remove('open'); });
  if(!isOpen) item.classList.add('open');
}

// ── CUSTOMIZATION RENDERER ────────────────────────────

// ── CUSTOMIZATION FLOWING LAYOUT ────────────────────────
// Wraps each enabled section's HTML (already built by initCustomizationRenderer)
// into a single flowing page: every section is visible at once, stacked as
// its own labeled card, no forced order and no "Continue" gating. Section
// count is whatever the product actually has configured — 2 sections
// enabled = 2 cards, 5 = 5.
function _cbwFallbackTitle(key) {
  var map = {
    photo: 'Upload Your Photos', text_fields: 'A Few Details', select_model: 'Choose an Option',
    colour_combos: 'Choose the Colour', text_colours: 'Text Colour', size_options: 'Select Size',
    pack_options: 'Pack Size', suggestion_box: 'Special Instructions', personalisation: 'Personalise'
  };
  return map[key] || 'Customise';
}

function _buildWizardShell(steps, cfg) {
  var html = '<div class="cflow">';
  if (cfg.show_header !== false) {
    html += '<div class="custom-card-title">' + (cfg.card_title || 'Customise Your Order') + '</div>';
  }

  steps.forEach(function(st, i) {
    var label = st.title || _cbwFallbackTitle(st.key);
    var bodyHtml = st.body;
    var badgeHtml = '';
    // The section's own body usually repeats its title as an internal
    // .custom-label (e.g. "Pick your colours" again inside the combo grid).
    // The card header already shows that title, so strip the duplicate —
    // but keep any trailing badge (like a "FREE" pill).
    var m = bodyHtml.match(/^(<div class="custom-block">)<div class="custom-label"[^>]*>([\s\S]*?)<\/div>/);
    if (m) {
      var badgeMatch = m[2].match(/(<span[\s\S]*<\/span>)\s*$/);
      if (badgeMatch) badgeHtml = ' ' + badgeMatch[1];
      bodyHtml = bodyHtml.slice(0, m.index) + m[1] + bodyHtml.slice(m.index + m[0].length);
    }
    html += '<div class="cflow-card">';
    html += '<div class="cflow-card-eyebrow"><span class="cflow-step-num">' + (i + 1) + '</span> ' + label + badgeHtml + '</div>';
    if (st.subtitle) html += '<div class="cflow-card-sub">' + st.subtitle + '</div>';
    html += bodyHtml;
    html += '</div>';
  });

  html += '</div>'; // cflow
  return html;
}

function initCustomizationRenderer() {
  var dataEl = document.getElementById('customizationJsonData');
  var container = document.getElementById('customizationFields');
  if (!dataEl || !container) return;
  var cfg;
  try { cfg = JSON.parse(dataEl.textContent); } catch(e) { console.warn('Customization parse error:', e); return; }
  if (!cfg || !cfg.sections) return;
  var s = cfg.sections; var html = '';
  var steps = [];

  if (cfg.show_header !== false) {
    html += '<div class="custom-card-title">' + (cfg.card_title || 'Customise Your Order') + '</div>';
  }

  (cfg.section_order || []).forEach(function(key) {
    var sec = s[key]; if (!sec || !sec.enabled) return;
    var _htmlStart = html.length;

    if (key === 'photo') {
      if (!sec.slots || sec.slots.length === 0) return;
      var anyPhotoRequired = sec.slots.some(function(sl) { return !!sl.required; });
      html += '<div class="custom-block">';
      html += '<div class="custom-label" style="font-size:0.8rem;font-weight:800;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:14px;">';
      html += (sec.title || '📸 UPLOAD YOUR PHOTOS') + (anyPhotoRequired ? ' <span style="color:var(--red)">*</span>' : ' <span style="font-size:0.72rem;color:var(--text-muted);font-weight:400;text-transform:none;letter-spacing:normal;">(optional)</span>') + '</div>';
      sec.slots.forEach(function(sl, i) {
        var slotId = 'cu_p' + i;
        var req = sl.required ? ' required' : '';
        html += '<div style="margin-bottom:14px;">';
        html += '<label style="font-size:0.82rem;font-weight:600;margin-bottom:8px;display:flex;align-items:center;gap:5px;color:var(--charcoal);">' +
                (sl.label || ('Photo ' + (i+1))) +
                (sl.required ? ' <span style="color:var(--red)">*</span>' : '<span style="font-size:0.72rem;color:var(--text-muted);font-weight:400;">(optional)</span>') +
                '</label>';
        // Upload area
        html += '<label for="' + slotId + '" id="' + slotId + '_zone" style="' +
                'display:flex;align-items:center;gap:16px;padding:14px 18px;' +
                'border:2px dashed #d0d0d0;border-radius:12px;cursor:pointer;' +
                'background:#fafaf9;transition:all 0.2s;min-height:68px;position:relative;"' +
                ' onmouseover="this.style.borderColor=\'var(--teal)\';this.style.background=\'#f0faf5\'"' +
                ' onmouseout="this.style.borderColor=\'#d0d0d0\';this.style.background=\'#fafaf9\'">';
        // Hidden file input — no forced 'capture' attribute, so mobile browsers
        // show their normal picker (choose Camera or Gallery) instead of
        // jumping straight into the camera app.
        html += '<input type="file" id="' + slotId + '" name="custom_photo_' + i + '" ' +
                'accept="image/*"' + req +
                ' onchange="previewCustomPhoto(this,' + i + ')" style="display:none;">';
        html += '<div id="cuPhotoSlot' + i + '" style="display:flex;align-items:center;gap:14px;width:100%;">';
        // Camera icon
        html += '<div style="width:44px;height:44px;border-radius:10px;background:var(--teal);display:flex;align-items:center;justify-content:center;flex-shrink:0;">' +
                '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
                '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>' +
                '<circle cx="12" cy="13" r="4"/></svg></div>';
        html += '<div><div style="font-size:0.88rem;font-weight:600;color:var(--charcoal);">' +
                'Click to upload ' + (sl.label || ('Photo ' + (i+1))) + '</div>' +
                '<div style="font-size:0.75rem;color:var(--text-muted);margin-top:2px;">JPG, PNG, WEBP · Max 10MB</div></div>';
        html += '</div></label>';
        // Thumbnail preview area
        html += '<div id="cuPreview' + i + '" style="display:none;margin-top:8px;border-radius:10px;overflow:hidden;border:2px solid var(--teal);">' +
                '<img id="cuPreviewImg' + i + '" src="" style="width:100%;max-height:180px;object-fit:contain;background:#f8f8f8;" alt="Preview"></div>';
        if (sl.required) {
          html += '<div class="field-err" id="err_' + slotId + '" data-for="' + slotId + '">⚠ ' + (sl.label || ('Photo ' + (i+1))) + ' is required</div>';
        }
        html += '</div>';
      });
      html += '</div>';
    }

    if (key === 'text_fields') {
      if (!sec.fields || sec.fields.length === 0) return;
      html += '<div class="custom-block">';
      sec.fields.forEach(function(f, i) {
        var fid = 'custom_field_' + i;
        html += '<div class="form-group" style="margin-bottom:12px;">';
        html += '<label class="form-label" style="font-size:0.82rem;">' + (f.label || ('Field ' + (i+1))) + (f.required ? ' <span style="color:var(--red)">*</span>' : '') + '</label>';
        html += '<input type="text" id="' + fid + '" name="' + fid + '" class="form-input" style="margin:0" placeholder="' + (f.placeholder || '') + '" maxlength="' + (f.max_chars || 200) + '"' + (f.required ? ' required' : '') + '>';
        if (f.required) {
          html += '<div class="field-err" id="err_' + fid + '" data-for="' + fid + '">⚠ ' + (f.label || ('Field ' + (i+1))) + ' is required</div>';
        }
        html += '</div>';
      });
      html += '</div>';
    }

    if (key === 'select_model') {
      if (!sec.options || sec.options.length === 0) return;
      html += '<div class="custom-block"><div class="custom-label">' + (sec.title || '🎭 Select Model') + ' <span style="color:var(--red)">*</span></div>';
      html += '<select id="custom_model" name="custom_model" class="form-input" style="margin:0" required><option value="">Choose…</option>';
      sec.options.forEach(function(o) { html += '<option>' + o + '</option>'; });
      html += '</select>';
      html += '<div class="field-err" id="err_custom_model" data-for="custom_model">⚠ Please select a ' + (sec.title || 'model').toLowerCase().replace('select the ', '').replace('select ', '') + '</div>';
      html += '</div>';
    }

    if (key === 'colour_combos') {
      if (!sec.combos || sec.combos.length === 0) return;
      html += '<div class="custom-block"><div class="custom-label">' + (sec.title || '🎨 Choose the Colour') + '</div><div class="custom-combo-grid">';
      sec.combos.forEach(function(c, i) {
        var n1 = (c.color1_name || '').trim();
        var n2 = (c.color2_name || '').trim();
        // Backward-compatible with older combos saved with one freeform "name" field.
        // Only join names that actually exist — no "Colour 2" placeholder text.
        var label = c.name ? c.name
                  : (n1 && n2) ? (n1 + ' / ' + n2)
                  : (n1 || n2 || ('Option ' + (i + 1)));
        // Show a single circle when the second colour is unnamed and identical
        // (or missing) — reads as one solid colour choice, like "Oak", "Walnut".
        var singleSwatch = !n2 && (!c.color2 || c.color2 === c.color1);
        html += '<label class="custom-combo-card' + (i === 0 ? ' selected' : '') + '" title="' + label + (c.description ? ' — ' + c.description : '') + '"><input type="radio" name="custom_colour_combo" value="' + label + '" style="display:none"' + (i === 0 ? ' checked' : '') + '>';
        html += '<div class="custom-combo-swatches"><span class="custom-swatch" style="background:' + c.color1 + '"></span>' + (singleSwatch ? '' : '<span class="custom-swatch" style="background:' + c.color2 + '"></span>') + '</div>';
        html += '<div class="custom-combo-name">' + label + '</div></label>';
      });
      html += '</div></div>';
    }

    if (key === 'text_colours') {
      var hasCol = (sec.slots || []).some(function(sl) { return sl.colours && sl.colours.length > 0; });
      if (!hasCol) return;
      html += '<div class="custom-block"><div class="custom-label">' + (sec.title || '✏️ Text Colour') + '</div>';
      (sec.slots || []).filter(function(sl) { return sl.colours && sl.colours.length; }).forEach(function(sl, i) {
        html += '<div style="margin-bottom:12px"><div class="custom-sublabel">' + sl.title + '</div><div class="custom-colour-chips">';
        sl.colours.forEach(function(col, ci) {
          html += '<label class="custom-colour-chip' + (ci === 0 ? ' selected' : '') + '" title="' + col.name + '"><input type="radio" name="custom_tc_' + i + '" value="' + col.name + '" style="display:none"' + (ci === 0 ? ' checked' : '') + '>';
          html += '<span class="custom-chip-swatch" style="background:' + col.hex + '"></span><span class="custom-chip-name">' + col.name + '</span></label>';
        });
        html += '</div></div>';
      });
      html += '</div>';
    }

    if (key === 'size_options') {
      if (!sec.sizes || sec.sizes.length === 0) return;
      html += '<div class="custom-block"><div class="custom-label">' + (sec.title || '📐 Select Size') + '</div><div class="size-pills">';
      sec.sizes.forEach(function(sz, i) {
        var extra = parseFloat(sz.extra_price) || 0;
        html += '<label class="size-pill' + (i === 0 ? ' active' : '') + '" style="cursor:pointer">' +
          '<input type="radio" name="custom_size" value="' + sz.label + '" data-extra="' + extra + '" style="display:none"' +
          (i === 0 ? ' checked' : '') +
          ' onchange="updateSizePrice(' + extra + '); document.querySelectorAll(\'.size-pill\').forEach(p=>p.classList.remove(\'active\')); this.closest(\'.size-pill\').classList.add(\'active\')">' +
          sz.label + (extra > 0 ? ' <span style=\'font-size:0.78em;color:var(--teal);\'>+₹' + extra + '</span>' : '') +
          '</label>';
      });
      // Set initial price if first size has extra cost
      if (sec.sizes.length > 0) {
        var firstExtra = parseFloat(sec.sizes[0].extra_price) || 0;
        if (firstExtra > 0) {
          setTimeout(function() { if (typeof updateSizePrice === 'function') updateSizePrice(firstExtra); }, 200);
        }
      }
      html += '</div></div>';
    }

    if (key === 'pack_options') {
      if (!sec.packs || sec.packs.length === 0) return;
      html += '<div class="custom-block"><div class="custom-label">📦 Pack Size</div><div class="custom-pack-grid">';
      sec.packs.forEach(function(p, i) {
        html += '<label class="custom-pack-card' + (i === 0 ? ' selected' : '') + '"><input type="radio" name="custom_pack" value="' + p.label + '" style="display:none"' + (i === 0 ? ' checked' : '') + ' onchange="selectPackCard(this)">';
        html += '<div class="custom-pack-label">' + p.label + '</div><div class="custom-pack-price">₹' + p.price + '</div>';
        if (p.discount_percent > 0) html += '<div class="custom-pack-off">' + p.discount_percent + '% off</div>';
        html += '</label>';
      });
      html += '</div></div>';
    }

    if (key === 'suggestion_box') {
      html += '<div class="custom-block"><div class="custom-label">' + (sec.title || '💬 Special Instructions') + '</div>';
      html += '<textarea name="custom_suggestion" class="form-input" style="margin:0" rows="3" maxlength="' + (sec.max_chars || 500) + '" placeholder="Any special notes or requests…"></textarea>';
      html += '</div>';
    }

    if (key === 'personalisation') {
      var persPrice = (sec.pricing === 'extra' && sec.extra_price > 0) ? ' <strong style="color:var(--teal)">(+₹' + sec.extra_price + ')</strong>' : ' <span style="background:var(--teal);color:#fff;font-size:0.68rem;padding:2px 7px;border-radius:999px;font-weight:700;">FREE</span>';
      html += '<div class="custom-block">';
      html += '<div class="custom-label">' + (sec.title || '✏️ Personalise') + ' ' + persPrice + '</div>';

      // No / Yes toggle
      html += '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">';
      html += '<label class="pers-toggle active" style="flex:1;padding:12px;text-align:center;border-radius:8px;border:2px solid var(--cream-border);cursor:pointer;font-weight:600;font-size:0.88rem;transition:all 0.2s;">';
      html += '<input type="radio" name="personalisation" value="no" checked onchange="togglePers(false)" style="display:none"> No Thanks</label>';
      html += '<label class="pers-toggle" style="flex:1;padding:12px;text-align:center;border-radius:8px;border:2px solid var(--cream-border);cursor:pointer;font-weight:600;font-size:0.88rem;transition:all 0.2s;">';
      html += '<input type="radio" name="personalisation" value="yes" onchange="togglePers(true)" style="display:none"> Yes, Personalise!</label>';
      html += '</div>';

      // Personalisation detail panel
      html += '<div id="persFields" style="display:none;">';

      // ── LIVE PREVIEW (shown at top, updated in real time) ──
      html += '<div style="margin-bottom:16px;">';
      html += '<div style="font-size:0.75rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:var(--text-muted);margin-bottom:6px;">🔍 Live Preview</div>';
      html += '<div id="persPreview" style="border:1.5px solid var(--cream-border);border-radius:12px;min-height:100px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;background:var(--cream);padding:18px 20px;transition:all 0.3s;position:relative;overflow:hidden;">';
      html += '<img id="persLogoPreviewImg" style="max-height:44px;max-width:100px;display:none;border-radius:4px;">';
      html += '<div id="persPreviewText" style="font-size:1.5rem;color:var(--charcoal);text-align:center;word-break:break-word;transition:font-family 0.2s;">Your preview will appear here</div>';
      html += '</div></div>';

      // ── TEXT SECTION ──
      html += '<div id="persTextSection">';
      html += '<div style="font-size:0.78rem;font-weight:700;color:var(--charcoal);margin-bottom:8px;">✏️ Your Text</div>';
      html += '<div id="persLines">';
      html += '<div class="form-group" style="margin-bottom:10px;"><label class="form-label" style="font-size:0.8rem;">Line 1</label>';
      html += '<input type="text" id="pers_line_0" name="pers_line_0" class="form-input pers-line-input" style="margin:0" maxlength="' + (sec.max_chars_per_line || 20) + '" placeholder="Enter text for Line 1…" oninput="updatePersPreview()">';
      html += '<div class="field-err" id="err_pers_line_0" data-for="pers_line_0">⚠ Please enter your personalisation text</div>';
      html += '</div>';
      html += '</div>';
      if ((sec.max_lines || 3) > 1) {
        html += '<button type="button" onclick="addPersLine(' + (sec.max_chars_per_line || 20) + ',' + (sec.max_lines || 3) + ')" style="margin-bottom:14px;padding:8px 14px;background:none;border:1.5px dashed var(--cream-border);border-radius:8px;cursor:pointer;font-size:0.82rem;color:var(--text-muted);display:block;width:100%;">+ Add Another Line</button>';
      }

      // Font selector with ON/OFF toggle
      var fonts = sec.fonts && sec.fonts.length > 0
        ? sec.fonts.filter(function(f){ return f.enabled !== false; })
        : [
            {name:'Inter',url:'Inter'},{name:'Pacifico',url:'Pacifico'},
            {name:'Oleo Script',url:'Oleo+Script'},{name:'Bungee',url:'Bungee'},
            {name:'Playfair Display',url:'Playfair+Display'},{name:'Dancing Script',url:'Dancing+Script'},
            {name:'Cinzel',url:'Cinzel'},{name:'Great Vibes',url:'Great+Vibes'}
          ];

      // Font toggle row
      html += '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">';
      html += '<label class="form-label" style="font-size:0.8rem;margin:0;">Font Style</label>';
      html += '<label style="display:flex;align-items:center;gap:6px;cursor:pointer;" onclick="togglePersFont()">';
      html += '<span style="font-size:0.72rem;color:var(--text-muted);">Custom Font</span>';
      html += '<div style="position:relative;width:40px;height:22px;">';
      html += '<div id="persFontTrack" style="position:absolute;inset:0;background:#ccc;border-radius:34px;transition:background 0.3s;"></div>';
      html += '<div id="persFontThumb" style="position:absolute;top:3px;left:3px;width:16px;height:16px;background:#fff;border-radius:50%;transition:transform 0.3s;box-shadow:0 1px 3px rgba(0,0,0,0.25);"></div>';
      html += '</div><span id="persFontToggleLbl" style="font-size:0.72rem;font-weight:700;color:#bbb;">OFF</span>';
      html += '</label></div>';

      html += '<div id="persFontGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px;margin-bottom:14px;opacity:0.35;pointer-events:none;transition:opacity 0.3s;">';
      fonts.forEach(function(f, fi) {
        var fontName = f.name || f;
        html += '<label class="pers-font-card' + (fi===0?' selected':'') + '" style="border:2px solid '+(fi===0?'var(--teal)':'var(--cream-border)')+';border-radius:8px;padding:8px 10px;cursor:pointer;text-align:center;transition:all 0.15s;" onclick="selectPersFont(\'' + fontName.replace(/'/g,"\\'") + '\',this)">';
        html += '<input type="radio" name="pers_font" value="' + fontName + '"' + (fi===0?' checked':'') + ' style="display:none">';
        html += '<div style="font-family:\'' + fontName + '\',sans-serif;font-size:1.1rem;margin-bottom:3px;">Aa</div>';
        html += '<div style="font-size:0.7rem;color:var(--text-muted);">' + fontName + '</div>';
        html += '</label>';
        loadGoogleFont(fontName);
      });
      html += '</div>';

      // Font Size selector — shown only when staff added sizes in the manage portal
      var persSizes = (sec.sizes || []).filter(function(z){ return z && (z.label || z.px); });
      if (persSizes.length) {
        html += '<label class="form-label" style="font-size:0.8rem;margin:0 0 8px;">Font Size</label>';
        html += '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px;">';
        persSizes.forEach(function(z, zi) {
          var zLabel = z.label || (z.px + 'px');
          var zPx = parseInt(z.px, 10) || 16;
          html += '<label class="pers-size-chip' + (zi===0?' selected':'') + '" style="border:2px solid '+(zi===0?'var(--teal)':'var(--cream-border)')+';border-radius:999px;padding:8px 16px;cursor:pointer;font-weight:600;font-size:0.82rem;transition:all 0.15s;background:'+(zi===0?'#F2FAF7':'#fff')+';" onclick="selectPersSize(' + zPx + ', this)">';
          html += '<input type="radio" name="pers_size" value="' + zLabel + ' (' + zPx + 'px)"' + (zi===0?' checked':'') + ' style="display:none">';
          html += zLabel + ' <span style="font-weight:400;color:var(--text-muted);font-size:0.74rem;">' + zPx + 'px</span>';
          html += '</label>';
        });
        html += '</div>';
      }

      html += '</div>'; // persTextSection

      // ── LOGO SECTION (visible alongside text, not a tab) ──
      html += '<div id="persLogoSection" style="margin-top:4px;margin-bottom:6px;">';
      html += '<div style="font-size:0.78rem;font-weight:700;color:var(--charcoal);margin-bottom:8px;">🏷️ Your Logo <span style="font-size:0.7rem;font-weight:400;color:var(--text-muted);">(optional)</span></div>';
      html += '<input type="hidden" name="pers_type" value="both">';
      html += '<label for="pers_logo_upload" class="photo-upload-slot" style="display:flex;align-items:center;gap:14px;padding:14px 18px;border:1.5px dashed var(--cream-border);border-radius:10px;cursor:pointer;background:var(--cream);min-height:58px;transition:border-color 0.2s;" onmouseover="this.style.borderColor=\'var(--teal)\'" onmouseout="this.style.borderColor=\'var(--cream-border)\'">';
      html += '<input type="file" id="pers_logo_upload" name="pers_logo" accept="image/*,image/svg+xml" style="display:none;" onchange="previewPersLogo(this)">';
      html += '<div id="persLogoSlot" style="display:flex;align-items:center;gap:14px;width:100%;"><span style="font-size:1.3rem;">🖼️</span>';
      html += '<div><div style="font-size:0.85rem;font-weight:600;color:var(--charcoal);">Click to upload your Logo</div><div style="font-size:0.73rem;color:var(--text-muted);">PNG, SVG · transparent background preferred</div></div></div>';
      html += '</label>';
      html += '</div>'; // persLogoSection

      html += '</div>'; // persFields
      html += '</div>'; // custom-block
    }

    // Extract whatever HTML this section just appended into its own wizard step
    if (html.length > _htmlStart) {
      var _body = html.slice(_htmlStart);
      html = html.slice(0, _htmlStart);
      steps.push({ key: key, title: sec.title, subtitle: sec.subtitle, body: _body });
    }
  });

  if (!steps.length) return;
  container.innerHTML = _buildWizardShell(steps, cfg);

  document.querySelectorAll('.custom-combo-card').forEach(function(card) {
    card.addEventListener('click', function() {
      document.querySelectorAll('.custom-combo-card').forEach(function(c) { c.classList.remove('selected'); });
      card.classList.add('selected'); var r = card.querySelector('input'); if (r) r.checked = true;
    });
  });
  document.querySelectorAll('.custom-colour-chip').forEach(function(chip) {
    chip.addEventListener('click', function() {
      var r = chip.querySelector('input'); if (!r) return;
      document.querySelectorAll('.custom-colour-chip input[name="' + r.name + '"]').forEach(function(x) { x.closest('.custom-colour-chip').classList.remove('selected'); });
      chip.classList.add('selected'); r.checked = true;
    });
  });
  document.querySelectorAll('.size-pill input').forEach(function(r) {
    r.addEventListener('change', function() {
      document.querySelectorAll('.size-pill input[name="' + r.name + '"]').forEach(function(x) { x.closest('.size-pill').classList.remove('active'); });
      r.closest('.size-pill').classList.add('active');
    });
    if (r.checked) r.closest('.size-pill').classList.add('active');
  });
}

// Clears everything the customer filled into the customization area after the
// item is added to the cart, so the previews/selections don't linger.

/* Keep the displayed price + highlighted pill in step with the size radio that is
   actually checked. Runs after the form is (re)built or reset, when the browser
   restores a form (back button), and again right before Add to Cart, so the price
   on screen always matches what is sent to the cart. */
function syncSizePrice() {
  var r = document.querySelector('#addToCartForm input[name="custom_size"]:checked') ||
          document.querySelector('#addToCartForm input[name="selected_size"]:checked');
  if (!r) return;
  var extra = parseFloat(r.getAttribute('data-extra'));
  if (isNaN(extra)) {
    var m = (r.getAttribute('onchange') || '').match(/updateSizePrice\(([-0-9.]+)\)/);
    extra = m ? parseFloat(m[1]) : 0;
  }
  if (typeof updateSizePrice === 'function') updateSizePrice(extra || 0);
  var pill = r.closest('.size-pill');
  if (pill) {
    document.querySelectorAll('#addToCartForm .size-pill').forEach(function(p) { p.classList.remove('active'); });
    pill.classList.add('active');
  }
}
window.addEventListener('pageshow', function() { setTimeout(syncSizePrice, 50); });

function resetCustomizationForm(form) {
  // 1) JSON-builder fields: re-render them from scratch (regenerates every
  //    photo slot, text field, dropdown, etc. in their pristine state).
  if (typeof initCustomizationRenderer === 'function' && document.getElementById('customizationFields')) {
    try { initCustomizationRenderer(); } catch (e) {}
  }
  // 2) Simple built-in photo upload (customization_type 'photo'/'miniature').
  var photoInput = document.getElementById('photoUpload') || document.getElementById('miniPhotoUpload');
  if (photoInput) photoInput.value = '';
  var photoPreview = document.getElementById('photoPreview');
  if (photoPreview) photoPreview.innerHTML = '<div class="file-upload-icon">📸</div><div class="file-upload-text">Click or drag to upload your photo</div>';
  // 3) Any leftover free-text / instruction inputs inside the form.
  if (form) {
    form.querySelectorAll('input[type="text"], textarea').forEach(function(el) { el.value = ''; });
  }
  // 4) Reset quantity back to 1.
  var qty = document.getElementById('qty');
  if (qty) qty.value = 1;
  // 5) The form is back on the first size — put the price back to match it.
  syncSizePrice();
}

function previewCustomPhoto(input, idx) {
  var slot = document.getElementById('cuPhotoSlot' + idx);
  var zone = document.getElementById('cu_p' + idx + '_zone');
  var previewWrap = document.getElementById('cuPreview' + idx);
  var previewImg  = document.getElementById('cuPreviewImg' + idx);

  if (!input.files || !input.files[0]) return;
  var file = input.files[0];
  var url  = URL.createObjectURL(file);
  var safeName = String(file.name || 'photo').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  var sizeLabel = file.size >= 1048576
    ? (file.size / 1048576).toFixed(1) + ' MB'
    : (file.size / 1024).toFixed(0) + ' KB';

  // Compact uploaded row: thumbnail · filename · green "Change" link
  if (slot) {
    slot.innerHTML =
      '<div class="cu-uploaded-row">' +
        '<img class="cu-uploaded-thumb" src="' + url + '" alt="Uploaded photo">' +
        '<div class="cu-uploaded-meta">' +
          '<div class="cu-uploaded-name">' + safeName + '</div>' +
          '<div class="cu-uploaded-size">' + sizeLabel + ' · Uploaded ✓</div>' +
        '</div>' +
        '<span class="cu-change-link">Change</span>' +
      '</div>';
  }
  // Solid teal border on zone to confirm success
  if (zone) {
    zone.style.borderColor = 'var(--teal)';
    zone.style.borderStyle = 'solid';
    zone.style.borderWidth = '1.5px';
    zone.style.background = '#F2FAF7';
  }
  // Larger thumbnail preview below
  if (previewWrap && previewImg) {
    previewImg.src = url;
    previewWrap.style.display = 'block';
  }
}
function selectPackCard(r) { document.querySelectorAll('.custom-pack-card').forEach(function(c){ c.classList.remove('selected'); }); r.closest('.custom-pack-card').classList.add('selected'); }

// ── PERSONALISATION FUNCTIONS ─────────────────────────
function togglePers(show) {
  var f = document.getElementById('persFields');
  if (f) f.style.display = show ? 'block' : 'none';
  // Update toggle button styles
  document.querySelectorAll('.pers-toggle').forEach(function(t) {
    var inp = t.querySelector('input');
    var isActive = inp && ((show && inp.value === 'yes') || (!show && inp.value === 'no'));
    t.style.borderColor = isActive ? 'var(--teal)' : 'var(--cream-border)';
    t.style.background = isActive ? 'rgba(26,155,119,0.08)' : '';
    t.style.color = isActive ? 'var(--teal)' : '';
  });
  // Gate fix: once the customer opts into personalisation, line 1 must be filled
  // before Add to Cart works. When they opt out, remove the requirement so it
  // doesn't block submission for customers who don't want personalisation.
  var firstLine = document.querySelector('input[name="pers_line_0"]');
  if (firstLine) {
    if (show) { firstLine.setAttribute('required', 'required'); }
    else {
      firstLine.removeAttribute('required');
      firstLine.classList.remove('field-invalid');
      var err = document.getElementById('err_pers_line_0');
      if (err) err.classList.remove('show');
    }
  }
  // Re-run the add-to-cart gate check immediately so the button state updates
  // without waiting for the next keystroke/blur.
  if (typeof _recheckAddToCartGate === 'function') _recheckAddToCartGate();
}

function togglePersType(type) {
  // no-op now — text and logo are both always visible when personalisation is ON
}

/* ── Font ON/OFF toggle ─────────────────────────────────────────────────── */
var _persFontEnabled = false;
function togglePersFont() {
  _persFontEnabled = !_persFontEnabled;
  var track = document.getElementById('persFontTrack');
  var thumb = document.getElementById('persFontThumb');
  var lbl   = document.getElementById('persFontToggleLbl');
  var grid  = document.getElementById('persFontGrid');
  if (track) track.style.background = _persFontEnabled ? 'var(--teal)' : '#ccc';
  if (thumb) thumb.style.transform  = _persFontEnabled ? 'translateX(18px)' : 'translateX(0)';
  if (lbl)  { lbl.textContent = _persFontEnabled ? 'ON' : 'OFF'; lbl.style.color = _persFontEnabled ? 'var(--teal)' : '#bbb'; }
  if (grid) { grid.style.opacity = _persFontEnabled ? '1' : '0.35'; grid.style.pointerEvents = _persFontEnabled ? 'auto' : 'none'; }
  if (!_persFontEnabled) {
    // clear font on preview
    var pt = document.getElementById('persPreviewText');
    if (pt) pt.style.fontFamily = 'inherit';
  }
  updatePersPreview();
}

function updatePersPreview() {
  var previewText = document.getElementById('persPreviewText');
  if (!previewText) return;
  var lines = [];
  document.querySelectorAll('.pers-line-input').forEach(function(inp) {
    if (inp.value.trim()) lines.push(inp.value.trim());
  });
  // If staff-defined size chips exist and one is selected, that size wins
  var _szChip = document.querySelector('.pers-size-chip.selected input');
  var _szPx = _szChip ? parseInt((_szChip.value.match(/\((\d+)px\)/) || [])[1], 10) : 0;
  if (lines.length) {
    previewText.style.whiteSpace = 'pre-line';
    previewText.textContent = lines.join('\n');
    previewText.style.color = 'var(--charcoal)';
    previewText.style.fontSize = _szPx ? _szPx + 'px' : (lines.length > 1 ? '1.2rem' : '1.5rem');
  } else {
    previewText.style.whiteSpace = 'normal';
    previewText.textContent = 'Your preview will appear here';
    previewText.style.color = '#aaa';
    previewText.style.fontSize = _szPx ? _szPx + 'px' : '1.2rem';
  }
  // Apply font
  if (_persFontEnabled) {
    var fontInput = document.querySelector('input[name="pers_font"]:checked');
    if (fontInput && fontInput.value) {
      previewText.style.fontFamily = "'" + fontInput.value + "', sans-serif";
      loadGoogleFont(fontInput.value);
    }
  } else {
    previewText.style.fontFamily = 'inherit';
  }
}

/* ── Logo file preview ──────────────────────────────────────────────────── */
function previewPersLogo(input) {
  var file = input.files[0];
  if (!file) return;
  var slot = document.getElementById('persLogoSlot');
  if (slot) slot.innerHTML = '<img src="' + URL.createObjectURL(file) + '" style="height:36px;border-radius:4px;object-fit:contain;flex-shrink:0;"><span style="font-size:0.82rem;color:var(--teal);font-weight:600;">' + file.name + '</span>';
  // Show logo in live preview
  var img = document.getElementById('persLogoPreviewImg');
  if (img) { img.src = URL.createObjectURL(file); img.style.display = 'block'; }
}

/* Font Size chips — staff-defined sizes from the manage portal builder */
function selectPersSize(px, el) {
  document.querySelectorAll('.pers-size-chip').forEach(function(c) {
    c.style.borderColor = 'var(--cream-border)';
    c.style.background = '#fff';
    c.classList.remove('selected');
  });
  if (el) {
    el.style.borderColor = 'var(--teal)';
    el.style.background = '#F2FAF7';
    el.classList.add('selected');
    var inp = el.querySelector('input');
    if (inp) inp.checked = true;
  }
  var previewText = document.getElementById('persPreviewText');
  if (previewText) previewText.style.fontSize = px + 'px';
}

function selectPersFont(fontName, el) {
  if (!_persFontEnabled) { togglePersFont(); }
  document.querySelectorAll('.pers-font-card').forEach(function(c) {
    c.style.borderColor = 'var(--cream-border)';
    c.classList.remove('selected');
  });
  if (el) { el.style.borderColor = 'var(--teal)'; el.classList.add('selected'); }
  var inp = el ? el.querySelector('input') : null;
  if (inp) inp.checked = true;
  var previewText = document.getElementById('persPreviewText');
  if (previewText && _persFontEnabled) {
    previewText.style.fontFamily = "'" + fontName + "', sans-serif";
    loadGoogleFont(fontName);
  }
}

function loadGoogleFont(fontName) {
  if (!fontName || fontName === 'Inter') return;
  var id = 'gf-' + fontName.toLowerCase().replace(/\s+/g, '-');
  if (document.getElementById(id)) return;
  var link = document.createElement('link');
  link.id = id; link.rel = 'stylesheet';
  link.href = 'https://fonts.googleapis.com/css2?family=' + encodeURIComponent(fontName) + ':wght@400;700&display=swap';
  document.head.appendChild(link);
}

var _persLines = 1;
function addPersLine(maxC, maxL) {
  if (_persLines >= maxL) { showToast('Max ' + maxL + ' lines', 'info'); return; }
  _persLines++;
  var d = document.createElement('div');
  d.className = 'form-group';
  d.style.marginBottom = '10px';
  d.innerHTML = '<label class="form-label" style="font-size:0.8rem;">Line ' + _persLines + '</label>' +
    '<input type="text" name="pers_line_' + (_persLines-1) + '" class="form-input pers-line-input" style="margin:0" maxlength="' + maxC + '" placeholder="Enter text for Line ' + _persLines + '…" oninput="updatePersPreview()">';
  var persLines = document.getElementById('persLines');
  if (persLines) persLines.appendChild(d);
  var inp = d.querySelector('input');
  if (inp) inp.addEventListener('input', updatePersPreview);
}

function initNavbar() {
  var toggle = document.getElementById('navToggle');
  var nav = document.getElementById('mainNav');
  if(toggle) toggle.addEventListener('click', function(){ nav&&nav.classList.toggle('open'); });
  document.addEventListener('click', function(e){ if(!e.target.closest('.navbar')) nav&&nav.classList.remove('open'); });
  // NOTE: profile dropdown click handling lives in an inline <script> in
  // base.html (not here) so it keeps working even if this file is served
  // stale from cache. Do not re-add a profileTrigger listener here — having
  // two independent toggle handlers on the same button cancels itself out.
}

// ── INIT ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  initNavbar(); initAddToCart(); initStarRating(); initHelpForm(); initFaqs();
  initCustomizationRenderer();
  initProductImageCycling();
  if(document.getElementById('descAccord')) toggleAccord('descAccord');
  setTimeout(function(){ document.querySelectorAll('.alert').forEach(function(el){ el.style.cssText+='opacity:0;transition:opacity 0.5s'; setTimeout(function(){ el.remove(); },500); }); }, 4000);
});

// ══════════════════════════════════════════════════════
//  CART DRAWER — Professional slide-in panel
// ══════════════════════════════════════════════════════
var CSRF_TOKEN = document.cookie.match(/csrftoken=([^;]+)/);
CSRF_TOKEN = CSRF_TOKEN ? CSRF_TOKEN[1] : '';

function openCartDrawer() {
  document.getElementById('cartDrawer').classList.add('open');
  document.getElementById('cartOverlay').style.display = 'block';
  document.body.style.overflow = 'hidden';
}
// Quick "Add to Cart" straight from a product grid/home card — only used for
// simple, non-customizable products (customizable ones link to View Details
// instead, since they need configuration first).
// Toggle a product's favorite/wishlist state — heart icon on product
// cards and the product detail page.
function toggleFavorite(productId, btn, event) {
  if (event) event.preventDefault();
  var wasFavorited = btn.classList.contains('is-favorited');
  btn.disabled = true;

  fetch('/favorites/toggle/' + productId + '/', {
    method: 'POST',
    headers: { 'X-CSRFToken': CSRF(), 'X-Requested-With': 'XMLHttpRequest' }
  }).then(function (r) {
    if (r.status === 302 || r.redirected) {
      // Not logged in — redirected to login page
      window.location.href = '/accounts/login/?next=' + window.location.pathname;
      throw new Error('redirect');
    }
    return r.json();
  }).then(function (data) {
    btn.disabled = false;
    if (data.success) {
      btn.classList.toggle('is-favorited', data.is_favorited);
      btn.setAttribute('aria-pressed', data.is_favorited ? 'true' : 'false');
      btn.setAttribute('aria-label', data.is_favorited ? 'Remove from favorites' : 'Add to favorites');
      // Little heart-pulse animation on state change
      btn.classList.remove('heart-pulse');
      void btn.offsetWidth; // restart animation
      btn.classList.add('heart-pulse');
      showToast(data.is_favorited ? '❤️ Added to favorites' : 'Removed from favorites', 'success');
      // Update any favorites-count badge in the nav
      var badge = document.getElementById('favBadgeNav');
      if (badge) {
        badge.textContent = data.favorite_count;
        badge.style.display = data.favorite_count > 0 ? 'flex' : 'none';
      }
      // If we're on the My Favorites page, remove the card when unfavorited
      if (!data.is_favorited && document.body.dataset.page === 'favorites') {
        var card = btn.closest('[data-fav-card]');
        if (card) {
          card.style.transition = 'opacity 0.25s, transform 0.25s';
          card.style.opacity = '0';
          card.style.transform = 'scale(0.92)';
          setTimeout(function () { card.remove(); }, 250);
        }
      }
    }
  }).catch(function (err) {
    btn.disabled = false;
    if (err.message !== 'redirect') {
      showToast('⚠️ Could not update favorites right now.', 'error');
    }
  });
}

function quickAddToCart(productId, btn) {
  var originalHTML = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = 'Adding…';

  fetch('/cart/add/' + productId + '/', {
    method: 'POST',
    headers: { 'X-CSRFToken': CSRF(), 'X-Requested-With': 'XMLHttpRequest' },
    body: new URLSearchParams({ quantity: 1 })
  }).then(function (r) { return r.json(); }).then(function (data) {
    btn.disabled = false;
    btn.innerHTML = originalHTML;
    if (data.success) {
      var badge = document.getElementById('cartBadgeNav');
      if (badge) { badge.textContent = data.cart_count; badge.style.display = 'flex'; }
      showToast('Added to cart!', 'success');
      if (typeof refreshCartDrawer === 'function') refreshCartDrawer();
    } else if (data.need_login) {
      window.location.href = data.redirect || '/accounts/login/';
    } else {
      showToast(data.message || 'Could not add to cart.', 'error');
    }
  }).catch(function () {
    btn.disabled = false;
    btn.innerHTML = originalHTML;
    showToast('⚠️ Network issue — please try again.', 'error');
  });
}

function refreshCartDrawer(callback) {
  fetch('/cart/drawer/', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
    .then(function(r) { return r.text(); })
    .then(function(html) {
      var drawer = document.getElementById('cartDrawer');
      if (drawer) drawer.innerHTML = html;
      if (typeof callback === 'function') callback();
    })
    .catch(function() {
      // If this fails, the drawer just keeps its last known content — still
      // open it so the customer isn't left with no feedback at all.
      if (typeof callback === 'function') callback();
    });
}
function closeCartDrawer() {
  document.getElementById('cartDrawer').classList.remove('open');
  document.getElementById('cartOverlay').style.display = 'none';
  document.body.style.overflow = '';
}

var _cartBusy = {};
function _cartCsrf() {
  var m = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
  if (m) return decodeURIComponent(m[1]);
  return (typeof CSRF_TOKEN !== 'undefined') ? CSRF_TOKEN : '';
}
function drawerUpdateCart(itemId, action) {
  if (_cartBusy[itemId]) return;           // ignore double-taps while a request is running
  _cartBusy[itemId] = true;
  var rowEl = document.getElementById('drawer-item-' + itemId);
  if (rowEl) rowEl.style.opacity = '0.55';
  fetch('/cart/update/' + itemId + '/', {
    method: 'POST',
    headers: { 'X-CSRFToken': _cartCsrf(), 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded' },
    body: 'action=' + action
  }).then(function(r) {
    if (!r.ok) throw new Error('http ' + r.status);
    return r.json();
  }).then(function(data) {
    _cartBusy[itemId] = false;
    if (!data.success) throw new Error('not ok');
    if (action === 'remove' || data.removed || data.already_removed) {
      var el = document.getElementById('drawer-item-' + itemId);
      if (el) el.remove();
      var items = document.querySelectorAll('.cart-drawer-item');
      if (items.length === 0) {
        var body = document.getElementById('cartDrawerBody');
        if (body) body.innerHTML = '<div class="cart-drawer-empty"><div style="font-size:3.5rem;margin-bottom:16px;">🛒</div><div style="font-weight:700;font-size:1rem;margin-bottom:6px;">Your cart is empty</div><div style="font-size:0.85rem;color:var(--text-muted);">Add items to get started</div></div>';
      }
    } else {
      if (rowEl) rowEl.style.opacity = '';
      var qEl = document.getElementById('drawer-qty-' + itemId);
      if (qEl) qEl.textContent = data.quantity;
      var pEl = document.getElementById('drawer-price-' + itemId);
      if (pEl) pEl.textContent = '₹' + parseFloat(data.item_total || 0).toFixed(2);
    }
    // Update totals
    var totalEl = document.getElementById('drawerTotal');
    if (totalEl) totalEl.textContent = '₹' + parseFloat(data.cart_total || 0).toFixed(2);
    var subEl = document.getElementById('drawerSubtotal');
    if (subEl) subEl.textContent = '₹' + parseFloat(data.cart_subtotal || 0).toFixed(2);
    var dParcelRow = document.getElementById('drawerParcelChargeRow');
    var dParcelEl = document.getElementById('drawerParcelCharge');
    if (dParcelEl) dParcelEl.textContent = '₹' + parseFloat(data.cart_parcel_charge || 0).toFixed(2);
    if (dParcelRow) dParcelRow.style.display = (data.cart_parcel_charge > 0) ? 'flex' : 'none';
    // Update nav badge
    var badge = document.getElementById('cartBadgeNav');
    if (badge) {
      var count = data.cart_count || 0;
      badge.textContent = count;
      badge.style.display = count > 0 ? 'flex' : 'none';
    }
    var countLabel = document.getElementById('cartCountLabel');
    if (countLabel) countLabel.textContent = data.cart_count || 0;
  }).catch(function() {
    // Anything went wrong (expired session, network, stale page): never fail
    // silently — tell the customer and reload the cart from the server.
    _cartBusy[itemId] = false;
    if (typeof showToast === 'function') showToast('Cart refreshed — please try again.', 'info');
    if (typeof refreshCartDrawer === 'function') refreshCartDrawer();
  });
}

function toggleDrawerCoupon() {
  var s = document.getElementById('drawerCouponSection');
  if (s) s.style.display = s.style.display === 'none' ? 'block' : 'none';
}
function toggleDrawerNotes() {
  var s = document.getElementById('drawerNotesArea');
  if (s) s.style.display = s.style.display === 'none' ? 'block' : 'none';
}
function applyThisCoupon(code) {
  var input = document.getElementById('drawerCouponInput');
  if (input) { input.value = code; applyDrawerCoupon(); }
}
function applyDrawerCoupon() {
  var code = (document.getElementById('drawerCouponInput') || {}).value || '';
  if (!code.trim()) return;
  fetch('/cart/coupon/', {
    method: 'POST',
    headers: { 'X-CSRFToken': CSRF_TOKEN, 'Content-Type': 'application/x-www-form-urlencoded' },
    body: 'coupon_code=' + encodeURIComponent(code.trim())
  }).then(function(r) { return r.json(); }).then(function(data) {
    var msg = document.getElementById('drawerCouponMsg');
    if (data.success) {
      if (msg) { msg.textContent = ''; }
      var totalEl = document.getElementById('drawerTotal');
      if (totalEl) totalEl.textContent = '₹' + parseFloat(data.total).toFixed(2);
      var codeEl = document.getElementById('drawerAppliedCode');
      if (codeEl) codeEl.textContent = code.trim().toUpperCase();
      var savingEl = document.getElementById('drawerAppliedSaving');
      if (savingEl) savingEl.textContent = Math.round(parseFloat(data.discount_amount || 0));
      var badge = document.getElementById('drawerAppliedCouponBadge');
      if (badge) badge.style.display = 'flex';
      var formRow = document.getElementById('drawerCouponFormRow');
      if (formRow) formRow.style.display = 'none';
      var avail = document.getElementById('drawerAvailableCoupons');
      if (avail) avail.style.display = 'none';
    } else {
      if (msg) { msg.textContent = data.message; msg.style.color = 'var(--red)'; }
    }
  });
}
function removeDrawerCoupon() {
  fetch('/cart/remove-coupon/', {
    method: 'POST',
    headers: { 'X-CSRFToken': CSRF_TOKEN }
  }).then(function(r) { return r.json(); }).then(function(data) {
    var totalEl = document.getElementById('drawerTotal');
    if (totalEl && data.total !== undefined) totalEl.textContent = '₹' + parseFloat(data.total).toFixed(2);
    var badge = document.getElementById('drawerAppliedCouponBadge');
    if (badge) badge.style.display = 'none';
    var formRow = document.getElementById('drawerCouponFormRow');
    if (formRow) formRow.style.display = 'block';
    var avail = document.getElementById('drawerAvailableCoupons');
    if (avail) avail.style.display = 'block';
    var input = document.getElementById('drawerCouponInput');
    if (input) input.value = '';
    var msg = document.getElementById('drawerCouponMsg');
    if (msg) msg.textContent = '';
  });
}
var _drawerGiftWrapBusy = false;
function toggleDrawerGiftWrap() {
  var cb = document.getElementById('drawerGiftWrap');
  if (_drawerGiftWrapBusy) { if(cb) cb.checked=!cb.checked; return; }
  _drawerGiftWrapBusy = true;
  fetch('/cart/gift-wrap/', {
    method: 'POST',
    headers: { 'X-CSRFToken': CSRF_TOKEN }
  }).then(function(r) { return r.json(); }).then(function(data) {
    if (cb) cb.checked = !!data.gift_wrap;
    var totalEl = document.getElementById('drawerTotal');
    if (totalEl && data.total !== undefined) totalEl.textContent = '₹' + parseFloat(data.total).toFixed(2);
  }).catch(function(){ if(cb) cb.checked=!cb.checked; })
    .finally(function(){ _drawerGiftWrapBusy=false; });
}



/* ── Long-press / hover product image cycling ─────────────────────────────
   Mobile: hold finger ≥500ms → images cycle every 700ms. Release → revert.
   Desktop: hover card → images cycle. Mouse-leave → revert.
   ───────────────────────────────────────────────────────────────────────── */
function initProductImageCycling() {
  document.querySelectorAll('.product-img-wrap[data-images]').forEach(function(wrap) {
    var rawUrls = (wrap.getAttribute('data-images') || '').split('|').filter(Boolean);
    if (rawUrls.length <= 1) return;
    var imgEl = wrap.querySelector('.prod-cycle-img');
    if (!imgEl) return;
    var origSrc = imgEl.src;
    var idx = 0;
    var holdTimer = null;
    var cycleTimer = null;
    function startCycle() {
      idx = 0;
      cycleTimer = setInterval(function() {
        idx = (idx + 1) % rawUrls.length;
        imgEl.src = rawUrls[idx];
      }, 700);
    }
    function stopCycle() {
      clearTimeout(holdTimer); clearInterval(cycleTimer);
      holdTimer = cycleTimer = null;
      imgEl.src = origSrc; idx = 0;
    }
    wrap.addEventListener('touchstart',  function() { holdTimer = setTimeout(startCycle, 500); }, {passive:true});
    wrap.addEventListener('touchend',    stopCycle, {passive:true});
    wrap.addEventListener('touchcancel', stopCycle, {passive:true});
    wrap.addEventListener('mouseenter', startCycle);
    wrap.addEventListener('mouseleave', stopCycle);
  });
}
/* ══════════════════════════════════════════════════════════════════════════
   SCROLL REVEAL — product cards & sections animate in as the user scrolls
══════════════════════════════════════════════════════════════════════════ */
function initScrollReveal() {
  if (!('IntersectionObserver' in window)) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var selectors = '.product-card, .yml-card, .fp-card, .review-card, .rvs-item, .cflow-card';
  var els = Array.prototype.slice.call(document.querySelectorAll(selectors));
  if (!els.length) return;

  // Stagger siblings inside the same grid so each row cascades left-to-right
  els.forEach(function (el) {
    var siblings = el.parentElement ? Array.prototype.filter.call(el.parentElement.children, function (c) {
      return c.classList && (c.classList.contains('product-card') || c.classList.contains('yml-card') ||
             c.classList.contains('fp-card') || c.classList.contains('review-card') ||
             c.classList.contains('rvs-item') || c.classList.contains('cflow-card'));
    }) : [el];
    var idx = siblings.indexOf(el);
    el.style.setProperty('--sr-delay', ((idx % 4) * 90) + 'ms');
    el.classList.add('sr-item');
  });

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('sr-in');
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -5% 0px' });

  els.forEach(function (el) { io.observe(el); });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initScrollReveal);
} else {
  initScrollReveal();
}
