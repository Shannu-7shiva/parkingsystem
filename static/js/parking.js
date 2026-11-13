// Virtual Parking Lot Map Controller

let allSlotsData = [];
let currentFilter = 'ALL';

async function loadParkingSlots() {
  try {
    const res = await fetch('/api/parking-slots');
    const json = await res.json();
    if (!json.success || !json.slots) return;

    allSlotsData = json.slots;
    updateFilterCounts();
    renderParkingWings();
  } catch (err) {
    console.error('Failed to load parking slots:', err);
  }
}

function updateFilterCounts() {
  const availCount = allSlotsData.filter(s => s.status === 'AVAILABLE').length;
  const occCount = allSlotsData.filter(s => s.status === 'OCCUPIED').length;

  const countAll = document.getElementById('countAll');
  const countAvail = document.getElementById('countAvail');
  const countOcc = document.getElementById('countOcc');

  if (countAll) countAll.innerText = allSlotsData.length;
  if (countAvail) countAvail.innerText = availCount;
  if (countOcc) countOcc.innerText = occCount;
}

function filterSlots(type) {
  currentFilter = type;
  renderParkingWings();
}

function renderParkingWings() {
  const northContainer = document.getElementById('slotsNorthWing');
  const southContainer = document.getElementById('slotsSouthWing');

  if (!northContainer || !southContainer) return;

  // Filter slots
  let filtered = allSlotsData;
  if (currentFilter === 'AVAILABLE') {
    filtered = allSlotsData.filter(s => s.status === 'AVAILABLE');
  } else if (currentFilter === 'OCCUPIED') {
    filtered = allSlotsData.filter(s => s.status === 'OCCUPIED');
  } else if (currentFilter === 'EV') {
    filtered = allSlotsData.filter(s => s.slot_type === 'EV');
  } else if (currentFilter === 'VIP') {
    filtered = allSlotsData.filter(s => s.slot_type === 'VIP');
  }

  // Split into North Wing (first 8 slots) and South Wing (remaining slots)
  const northSlots = filtered.filter(s => ['P01','P02','P03','P04','P05','P06','P07','P08'].includes(s.slot_number));
  const southSlots = filtered.filter(s => !['P01','P02','P03','P04','P05','P06','P07','P08'].includes(s.slot_number));

  northContainer.innerHTML = northSlots.length > 0 
    ? northSlots.map(s => buildBayCardHTML(s)).join('') 
    : `<div style="grid-column:1/-1; text-align:center; color:var(--text-sub); padding:1rem;">No bays match the active filter in North Wing.</div>`;

  southContainer.innerHTML = southSlots.length > 0
    ? southSlots.map(s => buildBayCardHTML(s)).join('')
    : `<div style="grid-column:1/-1; text-align:center; color:var(--text-sub); padding:1rem;">No bays match the active filter in South Wing.</div>`;
}

function buildBayCardHTML(slot) {
  const isOccupied = slot.status === 'OCCUPIED';
  const isReserved = slot.status === 'RESERVED';
  const statusClass = isOccupied ? 'occupied' : (isReserved ? 'reserved' : 'available');
  const carColor = getCarColor(slot.vehicle_plate || slot.slot_number);

  let typeBadge = `<span class="bay-type-tag tag-${slot.slot_type.toLowerCase()}">${slot.slot_type}</span>`;
  if (slot.slot_type === 'EV') {
    typeBadge = `<span class="bay-type-tag tag-ev"><i class="fa-solid fa-bolt"></i> EV CHARGE</span>`;
  } else if (slot.slot_type === 'VIP') {
    typeBadge = `<span class="bay-type-tag tag-vip"><i class="fa-solid fa-crown"></i> VIP</span>`;
  } else if (slot.slot_type === 'DISABLED') {
    typeBadge = `<span class="bay-type-tag tag-disabled"><i class="fa-solid fa-wheelchair"></i> ACCESSIBLE</span>`;
  }

  return `
    <div class="parking-bay ${statusClass}" onclick="openSlotDetailModal('${slot.slot_number}')">
      <div class="bay-header">
        <span class="bay-number">${slot.slot_number}</span>
        ${typeBadge}
      </div>

      <div class="bay-visual">
        ${isOccupied ? `
          <div class="css-car">
            <div class="car-body" style="background: ${carColor};">
              <div class="car-headlight left"></div>
              <div class="car-headlight right"></div>
              <div class="car-windshield-front"></div>
              <div class="car-roof"></div>
              <div class="car-windshield-rear"></div>
              <div class="car-taillight left"></div>
              <div class="car-taillight right"></div>
              <div class="car-mirror left"></div>
              <div class="car-mirror right"></div>
            </div>
          </div>
        ` : `
          <div class="empty-slot-guide">
            <i class="fa-solid ${isReserved ? 'fa-lock' : 'fa-circle-check'}"></i>
            <span style="font-weight:700;">${isReserved ? 'RESERVED' : 'BAY EMPTY'}</span>
            <span style="font-size:0.68rem; opacity:0.7;">Click to Manage</span>
          </div>
        `}
      </div>

      <div class="bay-footer">
        ${isOccupied ? `
          <div class="bay-plate-text">${slot.vehicle_plate}</div>
          <div class="bay-meta-time"><i class="fa-solid fa-clock"></i> Vehicle Active</div>
        ` : `
          <div style="font-size:0.75rem; text-align:center; font-weight:700; color:${isReserved ? 'var(--accent-amber)' : 'var(--accent-green)'}">
            ${slot.status}
          </div>
        `}
      </div>
    </div>
  `;
}

function openSlotDetailModal(slotNumber) {
  const slot = allSlotsData.find(s => s.slot_number === slotNumber);
  if (!slot) return;

  const title = document.getElementById('slotModalTitle');
  const body = document.getElementById('slotModalBody');
  const footer = document.getElementById('slotModalFooter');

  title.innerHTML = `<i class="fa-solid fa-square-parking" style="color:var(--accent-cyan);"></i> Bay ${slot.slot_number} Management`;

  if (slot.status === 'OCCUPIED') {
    body.innerHTML = `
      <div style="text-align:center; margin-bottom:1.25rem;">
        <span class="plate-badge" style="font-size:1.5rem; padding:8px 16px; margin-bottom:0.5rem;">${slot.vehicle_plate}</span>
        <div style="margin-top:0.5rem;"><span class="badge badge-occupied">CURRENTLY PARKED</span></div>
      </div>
      <div style="background:rgba(0,0,0,0.3); padding:1rem; border-radius:8px; font-size:0.88rem; line-height:2;">
        <div style="display:flex; justify-content:space-between;"><span>Bay Number:</span> <strong>${slot.slot_number}</strong></div>
        <div style="display:flex; justify-content:space-between;"><span>Bay Type:</span> <strong>${slot.slot_type}</strong></div>
        <div style="display:flex; justify-content:space-between;"><span>Vehicle Type:</span> <strong>${slot.vehicle_type || 'Car'}</strong></div>
      </div>
    `;

    footer.innerHTML = `
      <button class="btn btn-secondary btn-sm" onclick="closeSlotDetailModal()">Cancel</button>
      <button class="btn btn-danger btn-sm" onclick="checkoutModalVehicle('${slot.vehicle_plate}')">
        <i class="fa-solid fa-receipt"></i> Process Exit & Bill
      </button>
    `;
  } else {
    const isReserved = slot.status === 'RESERVED';
    body.innerHTML = `
      <div style="text-align:center; margin-bottom:1rem;">
        <h3 style="font-size:1.3rem; font-weight:800;">Slot ${slot.slot_number}</h3>
        <span class="badge ${isReserved ? 'badge-reserved' : 'badge-available'}">${slot.status}</span>
      </div>
      <p style="color:var(--text-muted); font-size:0.85rem; line-height:1.6; text-align:center;">
        ${isReserved 
          ? 'This bay is currently reserved. You can release it back to available status.' 
          : 'This slot is currently empty and available for incoming vehicles. You can reserve it for VIP or special access.'}
      </p>
    `;

    footer.innerHTML = `
      <button class="btn btn-secondary btn-sm" onclick="closeSlotDetailModal()">Close</button>
      <button class="btn ${isReserved ? 'btn-primary' : 'btn-primary'} btn-sm" onclick="toggleReservationFromModal('${slot.slot_number}')">
        <i class="fa-solid ${isReserved ? 'fa-lock-open' : 'fa-lock'}"></i> ${isReserved ? 'Release Reservation' : 'Reserve Bay'}
      </button>
    `;
  }

  document.getElementById('slotDetailModal').classList.add('active');
}

function closeSlotDetailModal() {
  document.getElementById('slotDetailModal').classList.remove('active');
}

async function toggleReservationFromModal(slotNumber) {
  closeSlotDetailModal();
  try {
    const res = await fetch(`/api/parking-slots/${slotNumber}/reserve`, { method: 'POST' });
    const json = await res.json();
    if (json.success) {
      showToast(json.message, 'success');
      loadParkingSlots();
    } else {
      showToast(json.message, 'error');
    }
  } catch (err) {
    showToast('Failed to toggle reservation: ' + err.message, 'error');
  }
}

async function checkoutModalVehicle(plate) {
  closeSlotDetailModal();
  showToast(`Processing checkout for ${plate}...`, 'info');
  try {
    const res = await fetch('/api/simulate-exit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plate_number: plate })
    });
    const json = await res.json();
    if (json.success && json.parking_action) {
      showToast(`Vehicle ${plate} vacated bay. Total amount: ₹${json.parking_action.amount}`, 'success');
      renderReceipt(json.parking_action);
      loadParkingSlots();
    }
  } catch (err) {
    showToast('Exit checkout failed: ' + err.message, 'error');
  }
}

function getCarColor(str) {
  const colors = ['#2563eb', '#dc2626', '#059669', '#d97706', '#7c3aed', '#0891b2', '#475569'];
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

// Initial Load & Polling
document.addEventListener('DOMContentLoaded', () => {
  loadParkingSlots();
  setInterval(loadParkingSlots, 3500);
});
