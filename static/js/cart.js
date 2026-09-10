/* ==========================================================================
   CRAVECART CART & DISH CUSTOMIZER ENGINE
   ========================================================================== */

let activeCustomizerItem = null;

document.addEventListener('DOMContentLoaded', () => {
  initDishCustomizer();
  initCartActions();
  initPromoCodeSystem();
});

// Initialize Customizer Modal Triggers
function initDishCustomizer() {
  document.addEventListener('click', async (e) => {
    const card = e.target.closest('.menu-item-card, .btn-customize-dish, .item-add-btn');
    if (!card) return;

    // If clicking add button directly, check if item has modifiers
    const itemId = card.dataset.itemId;
    if (!itemId) return;

    e.preventDefault();
    openCustomizerModal(itemId);
  });
}

// Fetch Dish Details & Open Modal
async function openCustomizerModal(itemId) {
  try {
    const res = await fetch(`/api/menu-items/${itemId}`);
    if (!res.ok) throw new Error('Failed to fetch item details');
    const item = await res.json();
    activeCustomizerItem = item;

    // Populate Modal Content
    const modal = document.getElementById('dish-customizer-modal');
    if (!modal) return;

    document.getElementById('customizer-item-name').textContent = item.name;
    document.getElementById('customizer-item-desc').textContent = item.description || '';
    document.getElementById('customizer-item-img').src = item.image_url;
    document.getElementById('customizer-base-price').textContent = `$${parseFloat(item.price).toFixed(2)}`;

    // Reset Quantity & Instructions
    const qtyElem = document.getElementById('customizer-qty');
    if (qtyElem) qtyElem.textContent = '1';
    const notesElem = document.getElementById('customizer-notes');
    if (notesElem) notesElem.value = '';

    // Render Modifier Groups
    const groupsContainer = document.getElementById('customizer-modifiers-container');
    groupsContainer.innerHTML = '';

    if (item.modifier_groups && item.modifier_groups.length > 0) {
      item.modifier_groups.forEach((grp, grpIdx) => {
        const isSingleChoice = grp.max_selection === 1;
        const inputType = isSingleChoice ? 'radio' : 'checkbox';
        const inputName = `mod_group_${grp.id}`;

        let optionsHtml = '';
        grp.options.forEach((opt, optIdx) => {
          const isOutOfStock = opt.stock_quantity !== null && opt.stock_quantity !== undefined && opt.stock_quantity <= 0;
          const isChecked = !isOutOfStock && (isSingleChoice ? (opt.is_default || optIdx === 0) : opt.is_default);
          const deltaText = opt.price_delta > 0 ? `+ $${parseFloat(opt.price_delta).toFixed(2)}` : (opt.price_delta < 0 ? `- $${parseFloat(-opt.price_delta).toFixed(2)}` : 'Included');
          const stockText = (opt.stock_quantity !== null && opt.stock_quantity !== undefined) ? 
            (isOutOfStock ? '<span class="tag tag-danger" style="font-size: 0.68rem; padding: 1px 5px; margin-left: 6px;">Sold Out</span>' : `<span style="font-size: 0.74rem; color: var(--text-muted); margin-left: 6px;">(${opt.stock_quantity} left today)</span>`) : '';

          optionsHtml += `
            <label class="modifier-option-card ${isOutOfStock ? 'disabled-option' : ''}" style="${isOutOfStock ? 'opacity: 0.55; cursor: not-allowed;' : ''}">
              <div style="display: flex; align-items: center; gap: 10px;">
                <input type="${inputType}" name="${inputName}" value="${opt.id}" 
                       data-name="${escapeHtml(opt.name)}" 
                       data-delta="${opt.price_delta}" 
                       ${isChecked ? 'checked' : ''} 
                       ${isOutOfStock ? 'disabled' : ''}
                       class="modifier-input">
                <span class="option-label" style="font-size: 0.92rem;">${escapeHtml(opt.name)} ${stockText}</span>
              </div>
              <span class="option-delta">${deltaText}</span>
            </label>
          `;
        });

        const choiceBadge = isSingleChoice ? '<span class="tag tag-primary">Select 1 Size</span>' : `<span class="tag tag-warning">Multi-Choice (Up to ${grp.max_selection})</span>`;
        const reqBadge = grp.is_required ? choiceBadge : '<span class="tag tag-secondary">Optional</span>';

        groupsContainer.innerHTML += `
          <div class="modifier-group" data-group-id="${grp.id}" data-required="${grp.is_required}" data-max="${grp.max_selection}">
            <div class="modifier-group-header">
              <span class="modifier-group-title">${escapeHtml(grp.name)}</span>
              ${reqBadge}
            </div>
            <div class="modifier-options-list">
              ${optionsHtml}
            </div>
          </div>
        `;
      });
    }

    // Bind Option Change Listeners to update Subtotal
    groupsContainer.querySelectorAll('.modifier-input').forEach(input => {
      input.addEventListener('change', updateCustomizerTotal);
    });

    updateCustomizerTotal();
    modal.classList.add('active');
  } catch (err) {
    console.error('Error opening customizer:', err);
    window.showToast('Could not load dish options', 'error');
  }
}

// Close Modal
window.closeCustomizerModal = function() {
  const modal = document.getElementById('dish-customizer-modal');
  if (modal) modal.classList.remove('active');
};

// Quantity Controls inside Customizer
window.changeCustomizerQty = function(delta) {
  const qtyElem = document.getElementById('customizer-qty');
  if (!qtyElem) return;
  let current = parseInt(qtyElem.textContent, 10) || 1;
  current = Math.max(1, current + delta);
  qtyElem.textContent = current;
  updateCustomizerTotal();
};

// Recalculate Live Total in Customizer Modal
function updateCustomizerTotal() {
  if (!activeCustomizerItem) return;

  const basePrice = parseFloat(activeCustomizerItem.price);
  let extras = 0.0;

  const selectedInputs = document.querySelectorAll('#customizer-modifiers-container .modifier-input:checked');
  selectedInputs.forEach(input => {
    extras += parseFloat(input.dataset.delta || 0.0);
  });

  const qty = parseInt(document.getElementById('customizer-qty').textContent, 10) || 1;
  const total = (basePrice + extras) * qty;

  const totalBtn = document.getElementById('customizer-add-btn-label');
  if (totalBtn) {
    totalBtn.textContent = `Add to Order • $${total.toFixed(2)}`;
  }
}

// Submit Customizer Form to Cart API
window.addCustomizedItemToCart = async function(forceReplace = false) {
  if (!activeCustomizerItem) return;

  const qty = parseInt(document.getElementById('customizer-qty').textContent, 10) || 1;
  const notes = document.getElementById('customizer-notes').value.trim();

  // Collect selected modifiers
  const selectedModifiers = [];
  const selectedInputs = document.querySelectorAll('#customizer-modifiers-container .modifier-input:checked');
  selectedInputs.forEach(input => {
    selectedModifiers.push({
      name: input.dataset.name,
      price_delta: parseFloat(input.dataset.delta || 0.0)
    });
  });

  try {
    const res = await fetch('/api/cart/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        menu_item_id: activeCustomizerItem.id,
        quantity: qty,
        special_instructions: notes,
        modifiers: selectedModifiers,
        force_replace: forceReplace
      })
    });

    const data = await res.json();

    if (res.status === 409 && data.error === 'different_restaurant') {
      // Prompt user with sleek modal to clear cart from different restaurant
      const confirmReplace = await window.showConfirmDialog({
        title: 'Start Fresh Cart Order?',
        message: `Your cart currently contains items from ${data.current_restaurant}. Would you like to clear your current cart and start a new order with ${activeCustomizerItem.name}?`,
        confirmText: 'Yes, Clear & Add Dish',
        cancelText: 'Keep Current Cart',
        type: 'warning',
        icon: '🛒'
      });
      if (confirmReplace) {
        addCustomizedItemToCart(true);
      }
      return;
    }

    if (data.success) {
      window.showToast(data.message, 'success');
      closeCustomizerModal();
      updateHeaderCartBadge(data.cart_count);
      
      // If mini cart exists on page, refresh it
      refreshMiniCart();
    } else {
      window.showToast(data.message || 'Could not add item to cart', 'error');
    }
  } catch (err) {
    console.error('Add to cart error:', err);
    window.showToast('Network error while adding to cart', 'error');
  }
};

// Header Cart Badge Update
function updateHeaderCartBadge(count) {
  const badge = document.getElementById('header-cart-count');
  if (badge) {
    badge.textContent = count;
    badge.style.display = count > 0 ? 'flex' : 'none';
    badge.classList.remove('bounce');
    void badge.offsetWidth; // trigger reflow
    badge.classList.add('bounce');
  }
}

// Mini Cart Refresh
async function refreshMiniCart() {
  const miniCartItems = document.getElementById('mini-cart-items-list');
  const miniCartSubtotal = document.getElementById('mini-cart-subtotal');
  if (!miniCartItems || !miniCartSubtotal) return;

  try {
    const res = await fetch('/api/cart');
    const data = await res.json();

    if (!data.items.length) {
      miniCartItems.innerHTML = `
        <div style="text-align: center; color: var(--text-muted); padding: 20px 0; font-size: 0.88rem;">
          Your cart is empty. Add dishes to start your order!
        </div>
      `;
      miniCartSubtotal.textContent = '$0.00';
      return;
    }

    let itemsHtml = '';
    data.items.forEach(item => {
      itemsHtml += `
        <div class="mini-cart-item">
          <div>
            <div style="font-weight: 700; color: var(--secondary);">${item.quantity}x ${escapeHtml(item.item_name)}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">$${parseFloat(item.item_total).toFixed(2)}</div>
          </div>
          <button onclick="updateCartItemQty(${item.id}, -1)" style="color: var(--danger); font-size: 0.8rem; font-weight: 700;">Remove</button>
        </div>
      `;
    });

    miniCartItems.innerHTML = itemsHtml;
    miniCartSubtotal.textContent = `$${parseFloat(data.subtotal).toFixed(2)}`;
  } catch (err) {
    console.error('Failed to refresh mini cart:', err);
  }
}

// Quantity Updates in Cart Page
function initCartActions() {
  window.updateCartItemQty = async function(cartItemId, delta) {
    try {
      const res = await fetch('/api/cart/update-quantity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cart_item_id: cartItemId, change: delta })
      });
      const data = await res.json();
      updateHeaderCartBadge(data.count);

      // If on /cart page, reload to recalculate all tax/breakdowns
      if (window.location.pathname === '/cart') {
        window.location.reload();
      } else {
        refreshMiniCart();
      }
    } catch (err) {
      console.error('Error updating quantity:', err);
    }
  };

  window.removeCartItem = async function(cartItemId) {
    try {
      const res = await fetch('/api/cart/remove-item', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cart_item_id: cartItemId })
      });
      const data = await res.json();
      updateHeaderCartBadge(data.count);
      window.location.reload();
    } catch (err) {
      console.error('Error removing item:', err);
    }
  };
}

// Promo Code Engine
function initPromoCodeSystem() {
  const applyPromoBtn = document.getElementById('apply-promo-btn');
  const promoInput = document.getElementById('promo-code-input');

  if (applyPromoBtn && promoInput) {
    applyPromoBtn.addEventListener('click', async () => {
      const code = promoInput.value.trim();
      if (!code) {
        window.showToast('Please enter a promo code', 'info');
        return;
      }

      try {
        const res = await fetch('/api/cart/apply-promo', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code: code })
        });
        const data = await res.json();
        if (data.success) {
          window.showToast(data.message, 'success');
          setTimeout(() => window.location.reload(), 500);
        } else {
          window.showToast(data.message, 'error');
        }
      } catch (err) {
        window.showToast('Failed to apply promo code', 'error');
      }
    });
  }

  window.removeAppliedPromo = async function() {
    try {
      const res = await fetch('/api/cart/remove-promo', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        window.showToast('Promo code removed', 'info');
        setTimeout(() => window.location.reload(), 400);
      }
    } catch (err) {
      console.error(err);
    }
  };
}
