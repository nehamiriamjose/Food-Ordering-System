/* ==========================================================================
   CRAVECART REAL-TIME ORDER TRACKING & SVG MAP VISUALIZER
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initTrackingTimeline();
  initDeliveryMapRoute();
  initStatusSimulationControls();
});

const statusOrder = ['placed', 'confirmed', 'preparing', 'ready', 'picked_up', 'on_the_way', 'delivered'];

const statusDetails = {
  placed: { title: "Order Placed", desc: "Your order has been sent to the kitchen.", progress: 15 },
  confirmed: { title: "Order Confirmed", desc: "The restaurant has accepted your order.", progress: 30 },
  preparing: { title: "Preparing Food", desc: "Chef is crafting your fresh delicious meal.", progress: 50 },
  ready: { title: "Ready for Pickup", desc: "Your food is packed and awaiting courier pickup.", progress: 70 },
  picked_up: { title: "Courier Picked Up", desc: "Marcus has secured your order in insulated bag.", progress: 85 },
  on_the_way: { title: "Courier on the Way", desc: "Marcus is heading towards your location.", progress: 92 },
  delivered: { title: "Delivered & Enjoy!", desc: "Order delivered. Bon appétit!", progress: 100 }
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

  // Move Courier on Map based on progress
  animateMapCourier(currentIdx);
}

function initDeliveryMapRoute() {
  const canvas = document.getElementById('tracking-map-svg');
  if (!canvas) return;

  // SVG route path is rendered in HTML, initialize courier position
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

// Driver Call/Message Simulation Modal
window.contactCourier = function(action) {
  const msg = action === 'call' 
    ? "Connecting audio call to Courier Marcus Vance at (555) 876-5432..."
    : "Opening direct in-app messaging with Marcus: 'Hi Marcus, please ring bell #4B!'";
  window.showToast(msg, 'info');
};
