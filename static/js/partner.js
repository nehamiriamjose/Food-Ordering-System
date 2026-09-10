/* ==========================================================================
   RESTAURANT PARTNER DASHBOARD JS
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initMenuAvailabilityToggles();
  initKitchenOrderAdvanceButtons();
});

function initMenuAvailabilityToggles() {
  const toggles = document.querySelectorAll('.item-stock-toggle');
  toggles.forEach(toggle => {
    toggle.addEventListener('change', async (e) => {
      const itemId = toggle.dataset.itemId;
      try {
        const res = await fetch('/api/partner/menu/toggle-availability', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ item_id: itemId })
        });
        const data = await res.json();
        if (data.success) {
          const statusText = data.is_available ? 'In Stock (Available)' : 'Sold Out (Unavailable)';
          window.showToast(`Item status updated: ${statusText}`, data.is_available ? 'success' : 'info');
        }
      } catch (err) {
        console.error(err);
        window.showToast('Could not update stock status', 'error');
      }
    });
  });
}

function initKitchenOrderAdvanceButtons() {
  const advanceButtons = document.querySelectorAll('.kitchen-advance-btn');
  advanceButtons.forEach(btn => {
    btn.addEventListener('click', async () => {
      const orderNum = btn.dataset.orderNumber;
      const targetStatus = btn.dataset.targetStatus;

      try {
        const res = await fetch(`/api/orders/${orderNum}/advance-status`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: targetStatus })
        });
        const data = await res.json();
        if (data.success) {
          window.showToast(`Order ${orderNum} updated to ${targetStatus.toUpperCase()}`, 'success');
          setTimeout(() => window.location.reload(), 500);
        }
      } catch (err) {
        console.error(err);
      }
    });
  });
}
