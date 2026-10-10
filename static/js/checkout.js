/* ==========================================================================
   CRAVECART REALISTIC PAYMENT GATEWAY & MULTI-STEP CHECKOUT JS
   ========================================================================== */

let selectedTipAmount = 3.00;
let baseSubtotalWithFees = 0.00;
let currentActivePaymentMethod = 'Visa ending in 4242';
let qrTimerInterval = null;
let otpResendInterval = null;

document.addEventListener('DOMContentLoaded', () => {
  initAddressSelection();
  initTipSelector();
  initPaymentTabs();
  initCardPreviewLiveTyping();
  initUpiSubtabs();
  initNetBankingSelection();
  initPlaceOrderFlow();
});

/* --------------------------------------------------------------------------
   Address Selector
   -------------------------------------------------------------------------- */
function initAddressSelection() {
  const addressCards = document.querySelectorAll('.address-select-card:not(.saved-card-choice)');
  addressCards.forEach(card => {
    card.addEventListener('click', () => {
      addressCards.forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
    });
  });
}

/* --------------------------------------------------------------------------
   Tip Selector & Dynamic Total Calculations
   -------------------------------------------------------------------------- */
function initTipSelector() {
  const tipButtons = document.querySelectorAll('.tip-btn');
  const tipDisplay = document.getElementById('checkout-tip-display');
  const totalDisplay = document.getElementById('checkout-total-display');
  
  if (totalDisplay) {
    baseSubtotalWithFees = parseFloat(totalDisplay.dataset.baseTotal || 0.0);
  }

  tipButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      tipButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const amount = parseFloat(btn.dataset.tip || 0.0);
      selectedTipAmount = amount;

      if (tipDisplay) {
        tipDisplay.textContent = `$${amount.toFixed(2)}`;
      }

      if (totalDisplay) {
        const finalTotal = Math.max(0, baseSubtotalWithFees + amount);
        totalDisplay.textContent = `$${finalTotal.toFixed(2)}`;
      }
    });
  });
}

/* --------------------------------------------------------------------------
   Payment Method Tabs & Card Live Preview
   -------------------------------------------------------------------------- */
function initPaymentTabs() {
  const tabBtns = document.querySelectorAll('.payment-tab-btn');
  const tabContents = document.querySelectorAll('.payment-tab-content');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));

      btn.classList.add('active');
      const targetId = btn.dataset.tab;
      const targetContent = document.getElementById(targetId);
      if (targetContent) {
        targetContent.classList.add('active');
      }

      // Update current active payment method label
      if (targetId === 'tab-card') {
        const selCard = document.querySelector('.saved-card-choice.selected');
        if (selCard) {
          currentActivePaymentMethod = `${selCard.dataset.brand} ending in ${selCard.dataset.last4}`;
        } else {
          currentActivePaymentMethod = 'Debit/Credit Card';
        }
      } else if (targetId === 'tab-upi') {
        const selApp = document.querySelector('.upi-app-card.selected');
        currentActivePaymentMethod = selApp ? `${selApp.dataset.app} (${selApp.dataset.vpa})` : 'UPI (Unified Payments)';
      } else if (targetId === 'tab-netbanking') {
        const selBank = document.querySelector('.bank-option-card.selected');
        currentActivePaymentMethod = selBank ? `Net Banking (${selBank.dataset.bank})` : 'Net Banking';
      }
    });
  });

  // Saved Cards Selection
  const savedCardChoices = document.querySelectorAll('.saved-card-choice');
  savedCardChoices.forEach(card => {
    card.addEventListener('click', () => {
      savedCardChoices.forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');

      const brand = card.dataset.brand || 'Visa';
      const last4 = card.dataset.last4 || '4242';
      const exp = card.dataset.exp || '12/28';

      currentActivePaymentMethod = `${brand} ending in ${last4}`;

      // Update Visual Preview
      const previewBrand = document.getElementById('card-preview-brand');
      const previewNumber = document.getElementById('card-preview-number');
      const previewExpiry = document.getElementById('card-preview-expiry');

      if (previewBrand) previewBrand.textContent = brand.toUpperCase();
      if (previewNumber) previewNumber.textContent = `•••• •••• •••• ${last4}`;
      if (previewExpiry) previewExpiry.textContent = exp;
    });
  });
}

function initCardPreviewLiveTyping() {
  const inputNumber = document.getElementById('input-card-number');
  const inputExpiry = document.getElementById('input-card-expiry');
  const inputName = document.getElementById('input-card-name');
  const autofillBtn = document.getElementById('autofill-demo-card-btn');

  const previewBrand = document.getElementById('card-preview-brand');
  const previewNumber = document.getElementById('card-preview-number');
  const previewExpiry = document.getElementById('card-preview-expiry');
  const previewName = document.getElementById('card-preview-name');

  if (inputNumber) {
    inputNumber.addEventListener('input', (e) => {
      // Format 16 digits into 4-digit groups
      let val = e.target.value.replace(/\D/g, '').substring(0, 16);
      let formatted = val.match(/.{1,4}/g)?.join(' ') || val;
      e.target.value = formatted;

      if (previewNumber) {
        previewNumber.textContent = formatted || '•••• •••• •••• ••••';
      }

      // Brand Detection
      if (previewBrand) {
        if (val.startsWith('4')) previewBrand.textContent = 'VISA';
        else if (val.startsWith('51') || val.startsWith('52') || val.startsWith('55')) previewBrand.textContent = 'MASTERCARD';
        else if (val.startsWith('34') || val.startsWith('37')) previewBrand.textContent = 'AMEX';
        else if (val.startsWith('60') || val.startsWith('65')) previewBrand.textContent = 'RUPAY';
        else previewBrand.textContent = 'CARD';
      }

      if (val.length >= 4) {
        currentActivePaymentMethod = `${previewBrand?.textContent || 'Card'} ending in ${val.slice(-4)}`;
      }
    });
  }

  if (inputExpiry) {
    inputExpiry.addEventListener('input', (e) => {
      let val = e.target.value.replace(/\D/g, '').substring(0, 4);
      if (val.length >= 2) {
        val = val.substring(0, 2) + '/' + val.substring(2);
      }
      e.target.value = val;
      if (previewExpiry) previewExpiry.textContent = val || 'MM/YY';
    });
  }

  if (inputName) {
    inputName.addEventListener('input', (e) => {
      if (previewName) previewName.textContent = e.target.value || 'CARDHOLDER NAME';
    });
  }

  if (autofillBtn) {
    autofillBtn.addEventListener('click', () => {
      if (inputNumber) {
        inputNumber.value = '4532 8812 4099 7821';
        inputNumber.dispatchEvent(new Event('input'));
      }
      if (inputExpiry) {
        inputExpiry.value = '08/29';
        inputExpiry.dispatchEvent(new Event('input'));
      }
      if (inputName) {
        inputName.value = 'Alex Rivera';
        inputName.dispatchEvent(new Event('input'));
      }
      const cvv = document.getElementById('input-card-cvv');
      if (cvv) cvv.value = '842';

      window.showToast('Test Card auto-filled successfully!', 'success');
    });
  }
}

/* --------------------------------------------------------------------------
   UPI Subtabs & Verification
   -------------------------------------------------------------------------- */
function initUpiSubtabs() {
  const subtabBtns = document.querySelectorAll('.upi-subtab-btn');
  subtabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      subtabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const target = btn.dataset.subtab;
      document.getElementById('subtab-upi-apps').style.display = target === 'upi-apps' ? 'block' : 'none';
      document.getElementById('subtab-upi-id').style.display = target === 'upi-id' ? 'block' : 'none';
      document.getElementById('subtab-upi-qr').style.display = target === 'upi-qr' ? 'block' : 'none';

      if (target === 'upi-qr') {
        startQrCountdown();
        currentActivePaymentMethod = 'UPI Dynamic QR Code';
      }
    });
  });

  // UPI Apps Grid Selection
  const upiAppCards = document.querySelectorAll('.upi-app-card');
  const selectedUpiAppLabel = document.getElementById('selected-upi-app-label');

  upiAppCards.forEach(card => {
    card.addEventListener('click', () => {
      upiAppCards.forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');

      const appName = card.dataset.app;
      const vpa = card.dataset.vpa;
      if (selectedUpiAppLabel) {
        selectedUpiAppLabel.textContent = `${appName} (${vpa})`;
      }
      currentActivePaymentMethod = `${appName} (${vpa})`;
    });
  });

  // Verify UPI ID Button
  const verifyUpiBtn = document.getElementById('verify-upi-btn');
  const upiInput = document.getElementById('input-custom-upi-id');
  const upiStatus = document.getElementById('upi-verify-status');

  if (verifyUpiBtn && upiInput) {
    verifyUpiBtn.addEventListener('click', async () => {
      const vpa = upiInput.value.trim();
      if (!vpa) return;

      verifyUpiBtn.disabled = true;
      verifyUpiBtn.textContent = 'Checking...';

      try {
        const res = await fetch('/api/payment/verify-upi', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ upi_id: vpa })
        });
        const data = await res.json();

        if (data.success) {
          upiStatus.innerHTML = `✓ Verified: <strong>${data.account_holder}</strong> (${data.bank_network})`;
          upiStatus.style.color = 'var(--success)';
          currentActivePaymentMethod = `UPI (${data.upi_id})`;
          window.showToast(`UPI ID verified for ${data.account_holder}!`, 'success');
        } else {
          upiStatus.innerHTML = `✕ ${data.message}`;
          upiStatus.style.color = 'var(--danger)';
        }
      } catch (err) {
        upiStatus.textContent = 'Could not verify UPI ID';
      } finally {
        verifyUpiBtn.disabled = false;
        verifyUpiBtn.textContent = 'Verify';
      }
    });
  }
}

function startQrCountdown() {
  if (qrTimerInterval) clearInterval(qrTimerInterval);
  let secondsLeft = 298; // ~5 mins
  const countdownEl = document.getElementById('qr-countdown');

  qrTimerInterval = setInterval(() => {
    secondsLeft--;
    if (secondsLeft <= 0) {
      clearInterval(qrTimerInterval);
      if (countdownEl) countdownEl.textContent = '00:00 (Expired)';
      return;
    }
    const mins = Math.floor(secondsLeft / 60).toString().padStart(2, '0');
    const secs = (secondsLeft % 60).toString().padStart(2, '0');
    if (countdownEl) countdownEl.textContent = `${mins}:${secs}`;
  }, 1000);
}

/* --------------------------------------------------------------------------
   Net Banking Selection
   -------------------------------------------------------------------------- */
function initNetBankingSelection() {
  const bankCards = document.querySelectorAll('.bank-option-card');
  bankCards.forEach(card => {
    card.addEventListener('click', () => {
      bankCards.forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      currentActivePaymentMethod = `Net Banking (${card.dataset.bank})`;
    });
  });
}

/* --------------------------------------------------------------------------
   Audio Synthesizer for Payment Success & Tap Chime
   -------------------------------------------------------------------------- */
function playPaymentSuccessChime() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();

    // Harmonic triumphant chord: C5 -> E5 -> G5 -> C6
    const notes = [523.25, 659.25, 783.99, 1046.50];
    notes.forEach((freq, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, ctx.currentTime + (idx * 0.08));

      gain.gain.setValueAtTime(0, ctx.currentTime + (idx * 0.08));
      gain.gain.linearRampToValueAtTime(0.18, ctx.currentTime + (idx * 0.08) + 0.03);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + (idx * 0.08) + 0.6);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(ctx.currentTime + (idx * 0.08));
      osc.stop(ctx.currentTime + (idx * 0.08) + 0.65);
    });
  } catch (err) {
    console.log('Web Audio chime unavailable:', err);
  }
}

/* --------------------------------------------------------------------------
   Place Order & Bank 3D-Secure / UPI Gateway Simulation Flow
   -------------------------------------------------------------------------- */
function initPlaceOrderFlow() {
  const placeOrderBtn = document.getElementById('place-order-btn');
  const gatewayModal = document.getElementById('gateway-modal');
  if (!placeOrderBtn || !gatewayModal) return;

  const totalDisplay = document.getElementById('checkout-total-display');
  const finalTotalStr = totalDisplay ? totalDisplay.textContent : '$0.00';

  // OTP inputs auto-advance
  const otpBoxes = document.querySelectorAll('.otp-box');
  otpBoxes.forEach((box, idx) => {
    box.addEventListener('input', (e) => {
      if (e.target.value.length === 1 && idx < otpBoxes.length - 1) {
        otpBoxes[idx + 1].focus();
      }
    });
    box.addEventListener('keydown', (e) => {
      if (e.key === 'Backspace' && !e.target.value && idx > 0) {
        otpBoxes[idx - 1].focus();
      }
    });
  });

  const autofillOtpBtn = document.getElementById('autofill-otp-btn');
  if (autofillOtpBtn) {
    autofillOtpBtn.addEventListener('click', () => {
      const code = '849201';
      otpBoxes.forEach((box, i) => {
        box.value = code[i] || '';
      });
      otpBoxes[otpBoxes.length - 1].focus();
    });
  }

  // Trigger Checkout
  placeOrderBtn.addEventListener('click', () => {
    // Determine which payment tab is active
    const activeTabBtn = document.querySelector('.payment-tab-btn.active');
    const tabType = activeTabBtn ? activeTabBtn.dataset.tab : 'tab-card';

    // Show amounts in modal
    document.querySelectorAll('.gateway-amount-display').forEach(el => {
      el.textContent = finalTotalStr;
    });

    // Reset Gateway Modal State
    document.getElementById('gateway-phase-init').style.display = 'block';
    document.getElementById('gateway-phase-otp').style.display = 'none';
    document.getElementById('gateway-phase-upi').style.display = 'none';
    document.getElementById('gateway-phase-success').style.display = 'none';

    gatewayModal.classList.add('active');

    // Simulate Gateway Handshake (1.2 seconds)
    setTimeout(() => {
      document.getElementById('gateway-phase-init').style.display = 'none';

      if (tabType === 'tab-card') {
        // Show Card 3D-Secure OTP Screen
        document.getElementById('gateway-phase-otp').style.display = 'block';
        startOtpCountdown();
        if (otpBoxes[0]) otpBoxes[0].focus();
      } else if (tabType === 'tab-upi') {
        // Show UPI App Approval Screen
        document.getElementById('gateway-phase-upi').style.display = 'block';
        const upiHandleEl = document.getElementById('gateway-upi-handle');
        if (upiHandleEl) upiHandleEl.textContent = currentActivePaymentMethod;
      } else {
        // Net banking -> Instant authorization
        completeOrderTransaction();
      }
    }, 1200);
  });

  // Submit OTP Button
  const submitOtpBtn = document.getElementById('submit-otp-btn');
  if (submitOtpBtn) {
    submitOtpBtn.addEventListener('click', () => {
      submitOtpBtn.disabled = true;
      submitOtpBtn.textContent = 'Verifying Passcode...';
      setTimeout(() => {
        completeOrderTransaction();
      }, 900);
    });
  }

  // Simulate UPI App Approval Button
  const simulateUpiBtn = document.getElementById('simulate-upi-approve-btn');
  if (simulateUpiBtn) {
    simulateUpiBtn.addEventListener('click', () => {
      simulateUpiBtn.disabled = true;
      simulateUpiBtn.innerHTML = 'Approving in UPI App...';
      setTimeout(() => {
        completeOrderTransaction();
      }, 800);
    });
  }
}

function startOtpCountdown() {
  if (otpResendInterval) clearInterval(otpResendInterval);
  let timeLeft = 28;
  const timerEl = document.getElementById('otp-timer-count');

  otpResendInterval = setInterval(() => {
    timeLeft--;
    if (timeLeft <= 0) {
      clearInterval(otpResendInterval);
      if (timerEl) timerEl.textContent = '0:00';
      return;
    }
    if (timerEl) timerEl.textContent = `0:${timeLeft < 10 ? '0' + timeLeft : timeLeft}`;
  }, 1000);
}

async function completeOrderTransaction() {
  // Collect Address Data
  const selectedAddressCard = document.querySelector('.address-select-card.selected');
  let addressData = {
    label: 'Home',
    street: '742 Evergreen Terrace, Apt 4B',
    city: 'New York',
    zip_code: '10001'
  };

  if (selectedAddressCard) {
    addressData = {
      label: selectedAddressCard.dataset.label || 'Home',
      street: selectedAddressCard.dataset.street || '742 Evergreen Terrace',
      apartment: selectedAddressCard.dataset.apt || 'Apt 4B',
      city: selectedAddressCard.dataset.city || 'New York',
      zip_code: selectedAddressCard.dataset.zip || '10001'
    };
  }

  const instructionsInput = document.getElementById('delivery-instructions-input');
  const instructions = instructionsInput ? instructionsInput.value.trim() : 'Leave at door';

  try {
    const res = await fetch('/api/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        address: addressData,
        delivery_instructions: instructions,
        payment_method: currentActivePaymentMethod,
        tip: selectedTipAmount
      })
    });

    const data = await res.json();

    if (data.success) {
      // Show Success Phase in Modal
      document.getElementById('gateway-phase-init').style.display = 'none';
      document.getElementById('gateway-phase-otp').style.display = 'none';
      document.getElementById('gateway-phase-upi').style.display = 'none';
      document.getElementById('gateway-phase-success').style.display = 'block';

      // Update Points & Transaction ID
      const txEl = document.getElementById('gateway-tx-id');
      const ptsEl = document.getElementById('gateway-earned-points');
      if (txEl) txEl.textContent = `TXN-${Math.floor(10000000 + Math.random() * 90000000)}`;
      if (ptsEl) ptsEl.textContent = data.earned_points || '350';

      // Play audio chime!
      playPaymentSuccessChime();

      window.showToast('Payment verified & order placed successfully!', 'success');

      setTimeout(() => {
        window.location.href = data.redirect_url;
      }, 1500);
    } else {
      document.getElementById('gateway-modal').classList.remove('active');
      window.showToast(data.message || 'Could not process order', 'error');
    }
  } catch (err) {
    console.error('Checkout error:', err);
    document.getElementById('gateway-modal').classList.remove('active');
    window.showToast('Network error during checkout verification', 'error');
  }
}

