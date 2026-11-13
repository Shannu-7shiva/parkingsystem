// Dashboard Auto-Updating and Visualization Logic

let isUpdating = false;

async function refreshDashboardData() {
  if (isUpdating) return;
  isUpdating = true;

  try {
    const res = await fetch('/api/dashboard');
    const json = await res.json();
    if (!json.success || !json.data) return;

    const { summary, slots, recent_records } = json.data;

    // 1. Update Metrics
    document.getElementById('valTotalSlots').innerText = summary.total_slots;
    document.getElementById('valAvailableSlots').innerText = summary.available_slots;
    document.getElementById('valOccupiedSlots').innerText = summary.occupied_slots;
    document.getElementById('valReservedSlots').innerText = summary.reserved_slots;
    document.getElementById('valTodaysVehicles').innerText = summary.todays_vehicles;
    document.getElementById('valCurrentlyParked').innerText = summary.currently_parked;
    document.getElementById('valTodaysRevenue').innerText = `₹${summary.todays_revenue.toFixed(2)}`;
    document.getElementById('valAvgDuration').innerText = summary.average_parking_time_formatted;

    // 2. Render Virtual Slots in Mini Lot Grid
    renderMiniSlots(slots);

    // 3. Render Recent Records
    renderRecentTable(recent_records);
  } catch (err) {
    console.error('Error fetching dashboard metrics:', err);
  } finally {
    isUpdating = false;
  }
}

function renderMiniSlots(slots) {
  const container = document.getElementById('dashboardSlotsGrid');
  if (!container || !slots) return;

  container.innerHTML = slots.map(slot => {
    const isOccupied = slot.status === 'OCCUPIED';
    const isReserved = slot.status === 'RESERVED';
    const statusClass = isOccupied ? 'occupied' : (isReserved ? 'reserved' : 'available');

    // Pick car body color dynamically based on plate hash
    const carColor = getCarColor(slot.vehicle_plate || 'default');

    return `
      <div class="parking-bay ${statusClass}" onclick="handleMiniSlotClick('${slot.slot_number}', '${slot.status}', '${slot.vehicle_plate || ''}')">
        <div class="bay-header">
          <span class="bay-number">${slot.slot_number}</span>
          <span class="bay-type-tag tag-${slot.slot_type.toLowerCase()}">${slot.slot_type}</span>
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
              <i class="fa-solid ${isReserved ? 'fa-lock' : 'fa-square-parking'}"></i>
              <span>${isReserved ? 'RESERVED' : 'AVAILABLE'}</span>
            </div>
          `}
        </div>

        <div class="bay-footer">
          ${isOccupied ? `
            <div class="bay-plate-text">${slot.vehicle_plate || 'PARKED'}</div>
          ` : `
            <div style="font-size:0.7rem; text-align:center; color: ${isReserved ? 'var(--accent-amber)' : 'var(--accent-green)'}; font-weight:700;">
              ${slot.status}
            </div>
          `}
        </div>
      </div>
    `;
  }).join('');
}

function renderRecentTable(records) {
  const tbody = document.getElementById('recentActivityTbody');
  if (!tbody) return;

  if (!records || records.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; color:var(--text-sub); padding:1.5rem;">No recent parking records.</td></tr>`;
    return;
  }

  tbody.innerHTML = records.map(r => {
    const isParked = r.status === 'PARKED';
    const statusBadge = isParked 
      ? '<span class="badge badge-occupied" style="font-size:0.68rem;">PARKED</span>'
      : '<span class="badge badge-available" style="font-size:0.68rem;">COMPLETED</span>';

    return `
      <tr>
        <td>
          <a href="/vehicles/${r.plate_number}" style="text-decoration:none;">
            <span class="plate-badge" style="font-size:0.75rem; padding:2px 6px;">${r.plate_number}</span>
          </a>
        </td>
        <td><strong style="color:var(--text-main);">${r.slot_number}</strong></td>
        <td>${statusBadge}</td>
        <td style="color:${isParked ? 'var(--text-sub)' : '#34d399'}; font-weight:600;">
          ₹${r.amount ? r.amount.toFixed(2) : '0.00'}
        </td>
      </tr>
    `;
  }).join('');
}

function handleMiniSlotClick(slotNumber, status, plate) {
  if (status === 'OCCUPIED') {
    if (confirm(`Vehicle ${plate} is currently parked in slot ${slotNumber}. Would you like to process exit/checkout?`)) {
      processSlotExit(plate);
    }
  } else {
    toggleSlotReservation(slotNumber);
  }
}

async function processSlotExit(plate) {
  showToast(`Initiating exit for ${plate}...`, 'info');
  try {
    const res = await fetch('/api/simulate-exit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plate_number: plate })
    });
    const json = await res.json();
    if (json.success && json.parking_action) {
      showToast(`Vehicle ${plate} checked out successfully.`, 'success');
      renderReceipt(json.parking_action);
      refreshDashboardData();
    }
  } catch (err) {
    showToast('Failed to process exit: ' + err.message, 'error');
  }
}

async function toggleSlotReservation(slotNumber) {
  try {
    const res = await fetch(`/api/parking-slots/${slotNumber}/reserve`, { method: 'POST' });
    const json = await res.json();
    if (json.success) {
      showToast(json.message, 'success');
      refreshDashboardData();
    } else {
      showToast(json.message, 'error');
    }
  } catch (err) {
    showToast('Failed to update slot reservation: ' + err.message, 'error');
  }
}

function getCarColor(str) {
  const colors = ['#2563eb', '#dc2626', '#059669', '#d97706', '#7c3aed', '#0891b2', '#475569'];
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % colors.length;
  return colors[index];
}

// Initial Load & 3-Second Real-Time Polling
document.addEventListener('DOMContentLoaded', () => {
  refreshDashboardData();
  setInterval(refreshDashboardData, 3000);
});
