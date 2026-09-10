/* ==========================================================================
   CRAVECART MAIN CLIENT APPLICATION JS
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initToasts();
  initSearchAutocomplete();
  initFavoriteButtons();
  initRoleSwitcher();
  initLocationModal();
  initUserDropdown();
  initPartnerDropdown();
  initSearchKeyboardShortcut();
});

// Partner Portal Dropdown
function initPartnerDropdown() {
  const dropdownWrap = document.getElementById('partner-nav-dropdown');
  const triggerBtn = document.getElementById('partner-menu-trigger');
  if (!dropdownWrap || !triggerBtn) return;

  triggerBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    dropdownWrap.classList.toggle('active');
  });

  document.addEventListener('click', (e) => {
    if (!dropdownWrap.contains(e.target)) {
      dropdownWrap.classList.remove('active');
    }
  });
}

// Global Cmd+K / Ctrl+K search shortcut
function initSearchKeyboardShortcut() {
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      const input = document.getElementById('global-search-input');
      if (input) {
        input.focus();
        input.select();
      }
    }
  });
}

// Delivery / Pickup Mode Toggle
window.setOrderMode = function(mode, btn) {
  const toggle = document.getElementById('order-mode-toggle');
  if (!toggle) return;
  toggle.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const modeLabel = mode === 'pickup' ? 'Takeout / Pickup' : 'Express Delivery';
  showToast(`Switched mode to ${modeLabel}`, 'info');
};

// User Account Dropdown Menu
function initUserDropdown() {
  const dropdownWrap = document.getElementById('user-dropdown-wrap');
  const triggerBtn = document.getElementById('user-menu-trigger');
  if (!dropdownWrap || !triggerBtn) return;

  triggerBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    dropdownWrap.classList.toggle('active');
  });

  document.addEventListener('click', (e) => {
    if (!dropdownWrap.contains(e.target)) {
      dropdownWrap.classList.remove('active');
    }
  });
}

// Toast System
window.showToast = function(message, type = 'success') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';
  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(50px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
};

// ==========================================================================
// PROFESSIONAL CUSTOM CONFIRMATION & ALERT MODAL DIALOGS
// (Eliminates ugly browser native alert() and confirm() popup boxes)
// ==========================================================================
window.showConfirmDialog = function({
  title = 'Are you sure?',
  message = 'This action cannot be undone.',
  confirmText = 'Yes, Proceed',
  cancelText = 'Cancel',
  type = 'danger', // 'danger' | 'warning' | 'primary'
  icon = null
} = {}) {
  return new Promise((resolve) => {
    // Remove any existing modal dialog
    const existing = document.getElementById('custom-confirm-modal-backdrop');
    if (existing) existing.remove();

    if (!icon) {
      icon = type === 'danger' ? '🗑️' : type === 'warning' ? '⚠️' : '✨';
    }

    const backdrop = document.createElement('div');
    backdrop.id = 'custom-confirm-modal-backdrop';
    backdrop.className = 'custom-modal-backdrop';

    const btnClass = type === 'danger' ? 'custom-modal-btn-danger' : type === 'warning' ? 'custom-modal-btn-warning' : 'custom-modal-btn-primary';

    backdrop.innerHTML = `
      <div class="custom-modal-dialog">
        <div class="custom-modal-icon-wrap ${type}">
          <span>${icon}</span>
        </div>
        <h3 class="custom-modal-title">${title}</h3>
        <p class="custom-modal-message">${message}</p>
        <div class="custom-modal-actions">
          <button type="button" class="custom-modal-btn custom-modal-btn-cancel" id="custom-confirm-cancel-btn">${cancelText}</button>
          <button type="button" class="custom-modal-btn ${btnClass}" id="custom-confirm-accept-btn">${confirmText}</button>
        </div>
      </div>
    `;

    document.body.appendChild(backdrop);

    // Trigger smooth fade-in and scale animation
    requestAnimationFrame(() => {
      backdrop.classList.add('active');
    });

    function cleanUp(result) {
      backdrop.classList.remove('active');
      setTimeout(() => {
        backdrop.remove();
        resolve(result);
      }, 240);
    }

    const acceptBtn = document.getElementById('custom-confirm-accept-btn');
    const cancelBtn = document.getElementById('custom-confirm-cancel-btn');

    if (acceptBtn) acceptBtn.addEventListener('click', () => cleanUp(true));
    if (cancelBtn) cancelBtn.addEventListener('click', () => cleanUp(false));

    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop) cleanUp(false);
    });

    const keyHandler = (e) => {
      if (e.key === 'Escape') {
        document.removeEventListener('keydown', keyHandler);
        cleanUp(false);
      }
    };
    document.addEventListener('keydown', keyHandler);
  });
};

// Form confirmation helper for 1-line event wiring in templates
window.confirmAction = async function(e, title, message, confirmText = 'Yes, Delete', type = 'danger', icon = '🗑️') {
  if (e) {
    e.preventDefault();
    e.stopPropagation();
  }
  const target = e ? e.target : null;
  const form = target ? (target.tagName === 'FORM' ? target : target.closest('form')) : null;

  const confirmed = await window.showConfirmDialog({
    title,
    message,
    confirmText,
    cancelText: 'Cancel',
    type,
    icon
  });

  if (confirmed && form) {
    form.submit();
  }
  return false;
};

function initToasts() {
  // Check if any initial alerts exist to convert to toasts if needed
}

// Global Search Autocomplete
function initSearchAutocomplete() {
  const searchInputs = document.querySelectorAll('.global-search-input');
  
  searchInputs.forEach(input => {
    const parent = input.closest('.header-search-wrap') || input.parentElement;
    let popover = parent.querySelector('.search-suggestions-popover');

    if (!popover) {
      popover = document.createElement('div');
      popover.className = 'search-suggestions-popover';
      parent.appendChild(popover);
    }

    let debounceTimer;
    input.addEventListener('input', (e) => {
      const q = e.target.value.trim();
      clearTimeout(debounceTimer);

      if (q.length < 2) {
        popover.classList.remove('active');
        return;
      }

      debounceTimer = setTimeout(async () => {
        try {
          const res = await fetch(`/api/search/suggestions?q=${encodeURIComponent(q)}`);
          const data = await res.json();
          renderSuggestions(popover, data, q);
        } catch (err) {
          console.error('Search error:', err);
        }
      }, 250);
    });

    document.addEventListener('click', (e) => {
      if (!parent.contains(e.target)) {
        popover.classList.remove('active');
      }
    });
  });
}

function renderSuggestions(popover, data, query) {
  if (!data.restaurants.length && !data.dishes.length) {
    popover.innerHTML = `
      <div style="padding: 16px; text-align: center; color: var(--text-muted); font-size: 0.88rem;">
        No matches for "<strong>${escapeHtml(query)}</strong>"
      </div>
    `;
    popover.classList.add('active');
    return;
  }

  let html = '';
  if (data.restaurants.length) {
    html += '<div class="suggestion-section-title">Restaurants</div>';
    data.restaurants.forEach(r => {
      html += `
        <a href="/restaurants/${r.id}" class="suggestion-item">
          <img src="${r.image_url}" class="suggestion-thumb" alt="${escapeHtml(r.name)}">
          <div>
            <div style="font-weight: 700; font-size: 0.9rem; color: var(--secondary);">${escapeHtml(r.name)}</div>
            <div style="font-size: 0.78rem; color: var(--text-muted);">${escapeHtml(r.cuisine)} • ⭐ ${r.rating}</div>
          </div>
        </a>
      `;
    });
  }

  if (data.dishes.length) {
    html += '<div class="suggestion-section-title">Dishes</div>';
    data.dishes.forEach(d => {
      html += `
        <a href="/restaurants/${d.restaurant_id}" class="suggestion-item">
          <div>
            <div style="font-weight: 700; font-size: 0.9rem; color: var(--secondary);">${escapeHtml(d.name)}</div>
            <div style="font-size: 0.78rem; color: var(--text-muted);">$${parseFloat(d.price).toFixed(2)} • from ${escapeHtml(d.restaurant_name)}</div>
          </div>
        </a>
      `;
    });
  }

  html += `
    <a href="/search?q=${encodeURIComponent(query)}" style="display: block; padding: 10px 16px; text-align: center; font-size: 0.85rem; font-weight: 700; color: var(--primary); background: var(--bg-muted); border-top: 1px solid var(--border-color);">
      See all results for "${escapeHtml(query)}" →
    </a>
  `;

  popover.innerHTML = html;
  popover.classList.add('active');
}

// Favorite Toggle Buttons
function initFavoriteButtons() {
  document.addEventListener('click', async (e) => {
    const favBtn = e.target.closest('.card-favorite-btn, .fav-toggle-btn');
    if (!favBtn) return;
    
    e.preventDefault();
    e.stopPropagation();

    const restId = favBtn.dataset.restaurantId;
    const dishId = favBtn.dataset.dishId;

    try {
      const res = await fetch('/api/favorites/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ restaurant_id: restId, menu_item_id: dishId })
      });
      const data = await res.json();
      if (data.success) {
        if (data.is_favorite) {
          favBtn.classList.add('active');
          favBtn.innerHTML = '❤️';
          showToast('Saved to your favorites!', 'success');
        } else {
          favBtn.classList.remove('active');
          favBtn.innerHTML = '🤍';
          showToast('Removed from favorites', 'info');
        }

        // Update badge count in header
        const favCountBadge = document.getElementById('header-fav-count');
        if (favCountBadge) {
          favCountBadge.textContent = data.fav_count;
          favCountBadge.style.display = data.fav_count > 0 ? 'flex' : 'none';
        }
      }
    } catch (err) {
      console.error('Favorite error:', err);
      showToast('Could not update favorite status', 'error');
    }
  });
}

// Quick Demo Role Switcher
function initRoleSwitcher() {
  const roleButtons = document.querySelectorAll('.role-btn');
  roleButtons.forEach(btn => {
    btn.addEventListener('click', async (e) => {
      const targetRole = btn.dataset.role;
      try {
        const res = await fetch('/api/demo/switch-role', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ role: targetRole })
        });
        const data = await res.json();
        if (data.success) {
          showToast(`Switched view to ${targetRole.toUpperCase()}: ${data.name}`, 'info');
          setTimeout(() => {
            window.location.href = data.redirect;
          }, 300);
        }
      } catch (err) {
        console.error('Role switch failed:', err);
      }
    });
  });
}

// Interactive Location Picker Modal
window.openLocationModal = function() {
  const modal = document.getElementById('location-picker-modal');
  if (modal) {
    modal.classList.add('active');
    const input = document.getElementById('manual-location-input');
    if (input) setTimeout(() => input.focus(), 100);
  }
};

window.closeLocationModal = function() {
  const modal = document.getElementById('location-picker-modal');
  if (modal) modal.classList.remove('active');
};

window.selectPresetLocation = function(locName) {
  updateDeliveryLocation(locName);
};

window.saveManualLocation = function() {
  const input = document.getElementById('manual-location-input');
  if (!input || !input.value.trim()) {
    showToast('Please enter a valid address or area', 'warning');
    return;
  }
  updateDeliveryLocation(input.value.trim());
};

function updateDeliveryLocation(location) {
  const locElem = document.getElementById('current-location-text');
  if (locElem) locElem.textContent = location;
  closeLocationModal();
  showToast(`📍 Delivery address updated to: ${location}`, 'success');
  
  // Store in localStorage
  try {
    localStorage.setItem('cravecart_delivery_loc', location);
  } catch (e) {}
}

function initLocationModal() {
  // Load saved location on page startup if set
  try {
    const saved = localStorage.getItem('cravecart_delivery_loc');
    if (saved) {
      const locElem = document.getElementById('current-location-text');
      if (locElem) locElem.textContent = saved;
    }
  } catch (e) {}

  // Allow pressing Enter in manual address input
  const input = document.getElementById('manual-location-input');
  if (input) {
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        saveManualLocation();
      }
    });
  }

  // Close modal when clicking backdrop
  const modal = document.getElementById('location-picker-modal');
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeLocationModal();
    });
  }
}

// Universal Button Click Ripple & Tactile Feedback
function initButtonRipples() {
  document.addEventListener('click', (e) => {
    const targetBtn = e.target.closest('.btn, .role-btn, .category-card, .nav-icon-btn, .tip-btn');
    if (!targetBtn) return;

    // Create ripple element
    const ripple = document.createElement('span');
    ripple.className = 'ripple-wave';
    
    const rect = targetBtn.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = e.clientX - rect.left - size / 2;
    const y = e.clientY - rect.top - size / 2;

    ripple.style.width = ripple.style.height = `${size}px`;
    ripple.style.left = `${x}px`;
    ripple.style.top = `${y}px`;

    targetBtn.appendChild(ripple);
    setTimeout(() => ripple.remove(), 600);

    // Subtle audio micro-click synthesizer
    playSubtleTapSound();
  });
}

function playSubtleTapSound() {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(800, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(400, ctx.currentTime + 0.04);

    gain.gain.setValueAtTime(0.04, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.04);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start();
    osc.stop(ctx.currentTime + 0.05);
  } catch (err) {
    // Silent fallback
  }
}

// Floating Deal Badge & Offers Drawer System
function initDealsDrawer() {
  const dealTrigger = document.getElementById('floating-deal-trigger');
  const drawerModal = document.getElementById('deals-drawer-modal');
  const closeBtn = document.getElementById('close-deals-drawer-btn');

  if (dealTrigger && drawerModal) {
    dealTrigger.addEventListener('click', () => {
      drawerModal.classList.add('active');
    });
  }

  if (closeBtn && drawerModal) {
    closeBtn.addEventListener('click', () => {
      drawerModal.classList.remove('active');
    });
  }

  if (drawerModal) {
    drawerModal.addEventListener('click', (e) => {
      if (e.target === drawerModal) {
        drawerModal.classList.remove('active');
      }
    });
  }

  // 1-Click Apply Promo Codes from Drawer or Banners
  document.addEventListener('click', async (e) => {
    const promoBtn = e.target.closest('.apply-promo-quick-btn');
    if (!promoBtn) return;

    const code = promoBtn.dataset.code;
    if (!code) return;

    promoBtn.disabled = true;
    promoBtn.textContent = 'Applying...';

    try {
      const res = await fetch('/api/cart/apply-promo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: code })
      });
      const data = await res.json();

      if (data.success) {
        showToast(`Promo ${code} applied successfully! Saved $${data.discount.toFixed(2)}`, 'success');
        if (drawerModal) drawerModal.classList.remove('active');
        // If on cart or checkout page, reload to reflect discount
        if (window.location.pathname === '/cart' || window.location.pathname === '/checkout') {
          setTimeout(() => window.location.reload(), 600);
        }
      } else {
        showToast(data.message || 'Could not apply promo code', 'error');
      }
    } catch (err) {
      console.error('Promo error:', err);
      showToast('Could not apply promo code', 'error');
    } finally {
      promoBtn.disabled = false;
      promoBtn.textContent = 'Apply Now';
    }
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

document.addEventListener('DOMContentLoaded', () => {
  initButtonRipples();
  initDealsDrawer();
});
