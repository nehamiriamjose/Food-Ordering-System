/* ==========================================================================
   CRAVECART REAL-TIME ORDER TRACKING, DELIVERY CONFIRMATION & MAP
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initTrackingTimeline();
  initDeliveryMapRoute();
  initStatusSimulationControls();
  initCustomerDeliveryControls();
  initTrackingReviewModal();
});

const statusOrder = ['placed', 'confirmed', 'preparing', 'ready', 'picked_up', 'on_the_way', 'delivered'];

const statusDetails = {
  placed: { title: "Order Placed", desc: "Your order has been sent to the kitchen.", progress: 15 },
  confirmed: { title: "Order Confirmed", desc: "The restaurant has accepted your order.", progress: 30 },
  preparing: { title: "Preparing Food", desc: "Chef is crafting your fresh delicious meal.", progress: 50 },
  ready: { title: "Ready for Pickup", desc: "Your food is packed and awaiting courier pickup.", progress: 70 },
  picked_up: { title: "Courier Picked Up", desc: "Marcus has secured your order in insulated bag.", progress: 85 },
  on_the_way: { title: "Courier on the Way", desc: "Marcus is heading towards your location.", progress: 92 },
  delivered: { title: "Delivered & Completed! 🎉", desc: "Order delivered. Enjoy your meal and bon appétit!", progress: 100 }
};

function initTrackingTimeline() {
  const orderContainer = document.getElementById('tracking-container');
  if (!orderContainer) return;

  const currentStatus = orderContainer.dataset.orderStatus || 'placed';
  updateTrackingUI(currentStatus);
}

function updateTrackingUI(status) {
  const currentIdx = statusOrder.indexOf(status);
  if (currentIdx === -1) return;

  // Update progress bar width
  const progressFill = document.getElementById('timeline-progress-fill');
  if (progressFill) {
    const percentage = ((currentIdx) / (statusOrder.length - 1)) * 100;
    progressFill.style.width = `${percentage}%`;
  }

  // Update node classes
  const steps = document.querySelectorAll('.timeline-step');
  steps.forEach((step, idx) => {
    step.classList.remove('completed', 'active');
    if (idx < currentIdx) {
      step.classList.add('completed');
    } else if (idx === currentIdx) {
      step.classList.add('active');
    }
  });

  // Update Status Banner Title & Desc
  const titleElem = document.getElementById('current-status-title');
  const descElem = document.getElementById('current-status-desc');
  if (titleElem && descElem && statusDetails[status]) {
    titleElem.textContent = statusDetails[status].title;
    descElem.textContent = statusDetails[status].desc;
  }

  // Update status badge on top
  const statusBadge = document.getElementById('tracking-status-badge');
  if (statusBadge) {
    if (status === 'delivered') {
      statusBadge.className = 'tag tag-success';
      statusBadge.textContent = '✓ Delivered';
    } else {
      statusBadge.className = 'tag tag-primary';
      statusBadge.textContent = 'Live Tracking (' + status.replace('_', ' ').toUpperCase() + ')';
    }
  }

  // If status is delivered, update top action banner if present
  if (status === 'delivered') {
    const actionBannerWrap = document.getElementById('delivery-action-banner-wrap');
    const orderNumberElem = document.getElementById('tracking-order-number');
    const ordNum = orderNumberElem ? orderNumberElem.dataset.orderNumber : '';
    
    if (actionBannerWrap && !document.getElementById('delivery-completed-box')) {
      actionBannerWrap.innerHTML = `
        <div class="delivery-completed-banner" id="delivery-completed-box" style="background: linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%); border: 2px solid var(--success); border-radius: var(--radius-lg); padding: 22px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
          <div style="display: flex; align-items: center; gap: 14px;">
            <div style="font-size: 2.4rem; background: #FFF; width: 56px; height: 56px; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: var(--shadow-xs); flex-shrink: 0;">
              🎉
            </div>
            <div>
              <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                <h3 style="font-size: 1.25rem; font-weight: 800; color: #065F46; margin: 0;">Order Delivered Successfully!</h3>
                <span class="tag tag-success" style="font-weight: 800;">✓ Archived in History</span>
              </div>
              <p style="color: #047857; font-size: 0.88rem; margin: 0;">
                Your meal has been delivered. This order is saved permanently in your Order History.
              </p>
            </div>
          </div>
          <div style="display: flex; gap: 10px; flex-wrap: wrap;">
            <button type="button" class="btn btn-primary btn-sm open-tracking-review-btn" data-order="${ordNum}" style="font-weight: 800;">
              ⭐ Rate & Review Meal
            </button>
            <a href="/orders" class="btn btn-secondary btn-sm" style="font-weight: 700;">
              📜 View in Order History
            </a>
          </div>
        </div>
      `;
      // Re-attach review modal listener
      attachReviewTrigger();
    }
  }

  // Move Courier on Map based on progress
  animateMapCourier(currentIdx);
}

function initDeliveryMapRoute() {
  const canvas = document.getElementById('tracking-map-svg');
  if (!canvas) return;

  const orderContainer = document.getElementById('tracking-container');
  const currentStatus = orderContainer ? (orderContainer.dataset.orderStatus || 'placed') : 'placed';
  const idx = statusOrder.indexOf(currentStatus);
  animateMapCourier(Math.max(0, idx));
}

function animateMapCourier(statusIndex) {
  const courierMarker = document.getElementById('svg-courier-marker');
  const routePath = document.getElementById('svg-route-path');
  if (!courierMarker || !routePath) return;

  const totalLength = routePath.getTotalLength();
  const progressRatio = Math.min(1.0, statusIndex / (statusOrder.length - 1));
  const currentDistance = totalLength * progressRatio;

  const point = routePath.getPointAtLength(currentDistance);
  courierMarker.setAttribute('transform', `translate(${point.x - 20}, ${point.y - 20})`);
}

function initStatusSimulationControls() {
  const advanceBtn = document.getElementById('sim-advance-status-btn');
  const orderNumberElem = document.getElementById('tracking-order-number');

  if (advanceBtn && orderNumberElem) {
    const orderNumber = orderNumberElem.dataset.orderNumber;

    advanceBtn.addEventListener('click', async () => {
      advanceBtn.disabled = true;
      try {
        const res = await fetch(`/api/orders/${orderNumber}/advance-status`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
          window.showToast(`Order status updated to: ${data.new_status.replace('_', ' ').toUpperCase()}`, 'success');
          
          const orderContainer = document.getElementById('tracking-container');
          if (orderContainer) {
            orderContainer.dataset.orderStatus = data.new_status;
          }
          updateTrackingUI(data.new_status);
        }
      } catch (err) {
        console.error('Failed to advance order status:', err);
      } finally {
        advanceBtn.disabled = false;
      }
    });
  }
}

// Customer "I Have Received My Order" Handler
function initCustomerDeliveryControls() {
  const markDeliveredBtn = document.getElementById('customer-mark-delivered-btn');
  if (!markDeliveredBtn) return;

  markDeliveredBtn.addEventListener('click', async () => {
    const ordNum = markDeliveredBtn.dataset.order;
    const restName = markDeliveredBtn.dataset.rest || 'the restaurant';

    const confirmed = await window.showConfirmDialog({
      title: 'Confirm Order Delivery',
      message: `Have you received your order from ${restName}? Marking as delivered records it into your permanent Order History.`,
      confirmText: 'Yes, I Received My Order',
      cancelText: 'Not Yet',
      type: 'primary',
      icon: '🛵'
    });

    if (!confirmed) return;

    markDeliveredBtn.disabled = true;
    markDeliveredBtn.textContent = 'Updating...';

    try {
      const res = await fetch(`/api/orders/${ordNum}/mark-delivered`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await res.json();
      if (data.success) {
        window.showToast('🎉 Order confirmed delivered! Archived in Order History.', 'success');
        
        const orderContainer = document.getElementById('tracking-container');
        if (orderContainer) {
          orderContainer.dataset.orderStatus = 'delivered';
        }
        updateTrackingUI('delivered');
      } else {
        window.showToast(data.message || 'Could not update delivery status', 'error');
        markDeliveredBtn.disabled = false;
        markDeliveredBtn.textContent = '✓ I Have Received My Order';
      }
    } catch (err) {
      window.showToast('Network error while marking order delivered', 'error');
      markDeliveredBtn.disabled = false;
      markDeliveredBtn.textContent = '✓ I Have Received My Order';
    }
  });
}

// Tracking Review Modal
function initTrackingReviewModal() {
  attachReviewTrigger();

  let selectedStar = 5;
  const reviewModal = document.getElementById('tracking-review-modal');
  const closeBtn = document.getElementById('close-t-review-modal-btn');
  const submitBtn = document.getElementById('t-submit-review-btn');
  const stars = document.querySelectorAll('.t-star-rating-star');

  if (closeBtn && reviewModal) {
    closeBtn.addEventListener('click', () => reviewModal.classList.remove('active'));
  }

  stars.forEach(star => {
    star.addEventListener('click', () => {
      selectedStar = parseInt(star.dataset.star);
      stars.forEach((s, i) => {
        s.style.opacity = i < selectedStar ? '1' : '0.3';
      });
    });
  });

  if (submitBtn) {
    submitBtn.addEventListener('click', async () => {
      const ordNum = document.getElementById('t-review-order-number').value;
      const comment = document.getElementById('t-review-comment-input').value.trim();

      submitBtn.disabled = true;
      submitBtn.textContent = 'Submitting...';

      try {
        const res = await fetch(`/api/orders/${ordNum}/review`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ rating: selectedStar, comment: comment })
        });
        const data = await res.json();
        if (data.success) {
          window.showToast('⭐ Thank you! Your review has been recorded.', 'success');
          if (reviewModal) reviewModal.classList.remove('active');
        } else {
          window.showToast(data.message || 'Could not submit review', 'error');
        }
      } catch (err) {
        window.showToast('Error posting review', 'error');
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit Review';
      }
    });
  }
}

function attachReviewTrigger() {
  const reviewModal = document.getElementById('tracking-review-modal');
  document.querySelectorAll('.open-tracking-review-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const restName = btn.dataset.rest;
      const restTitle = document.getElementById('t-review-rest-title');
      if (restTitle && restName) {
        restTitle.textContent = `Rate ${restName}`;
      }
      if (reviewModal) reviewModal.classList.add('active');
    });
  });
}

// Driver Call/Message Simulation Modal
window.contactCourier = function(action) {
  const msg = action === 'call' 
    ? "Connecting audio call to Courier Marcus Vance at (555) 876-5432..."
    : "Opening direct in-app messaging with Marcus: 'Hi Marcus, please ring bell #4B!'";
  window.showToast(msg, 'info');
};
