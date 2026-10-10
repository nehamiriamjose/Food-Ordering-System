/* ==========================================================================
   COURIER DELIVERY PARTNER JS
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initCourierOnlineToggle();
  initCourierMissionActions();
});

function initCourierOnlineToggle() {
  const onlineToggle = document.getElementById('courier-online-switch');
  if (!onlineToggle) return;

  onlineToggle.addEventListener('change', async () => {
    try {
      const res = await fetch('/api/courier/toggle-online', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        const text = data.is_online ? "You are now ONLINE and ready for orders!" : "You are now OFFLINE. Shift paused.";
        const dot = document.getElementById('courier-top-status-dot');
        if (dot) {
          dot.className = 'status-indicator-dot ' + (data.is_online ? 'online' : 'offline');
        }
        if (window.showToast) window.showToast(text, data.is_online ? 'success' : 'info');
      }
    } catch (err) {
      console.error(err);
    }
  });
}

function initCourierMissionActions() {
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('.mission-step-btn');
    if (!btn) return;

    const orderNum = btn.dataset.orderNumber;
    const nextStatus = btn.dataset.nextStatus;
    if (!orderNum || !nextStatus) return;

    btn.disabled = true;
    const origText = btn.innerHTML;
    btn.innerHTML = '⏳ Updating...';

    try {
      const res = await fetch(`/api/orders/${orderNum}/advance-status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: nextStatus })
      });
      const data = await res.json();
      if (data.success) {
        let msg = `Delivery updated: ${nextStatus.replace('_', ' ').toUpperCase()}`;
        if (nextStatus === 'delivered') {
          msg = `🎉 Order #${orderNum} delivered! Payout earned. You are now FREE for new delivery missions.`;
        } else if (nextStatus === 'picked_up') {
          msg = `📦 Order #${orderNum} picked up from restaurant! Safe travels.`;
        } else if (nextStatus === 'on_the_way') {
          msg = `🛵 En route to customer for Order #${orderNum}!`;
        }
        if (window.showToast) window.showToast(msg, 'success');
        setTimeout(() => window.location.reload(), 600);
      } else {
        btn.disabled = false;
        btn.innerHTML = origText;
        if (window.showToast) window.showToast(data.message || 'Failed to update delivery status', 'error');
      }
    } catch (err) {
      btn.disabled = false;
      btn.innerHTML = origText;
      console.error(err);
      if (window.showToast) window.showToast('Network error while updating delivery', 'error');
    }
  });
}

window.simulateCashout = function(amt = 0) {
  const formatted = typeof amt === 'number' && amt > 0 ? `$${amt.toFixed(2)}` : '$0.00';
  if (amt <= 0) {
    if (window.showToast) window.showToast("No payout balance available right now. Complete deliveries to earn money!", "info");
  } else {
    if (window.showToast) window.showToast(`Instant payout initiated! ${formatted} transferred to your linked payout account.`, "success");
  }
};
