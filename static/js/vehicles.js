// Vehicles, History, Blacklist, and Settings Controller

// ----------------------------------------------------
// 1. Vehicles Registry
// ----------------------------------------------------
async function fetchVehicles() {
  const search = document.getElementById('vehicleSearchInput')?.value || '';
  const type = document.getElementById('vehicleTypeFilter')?.value || 'all';
  const status = document.getElementById('vehicleStatusFilter')?.value || 'all';

  const tbody = document.getElementById('vehiclesTableBody');
  if (!tbody) return;

  try {
    const res = await fetch(`/api/vehicles?search=${encodeURIComponent(search)}&type=${encodeURIComponent(type)}&status=${encodeURIComponent(status)}`);
    const json = await res.json();
    if (!json.success) return;

    const countDisp = document.getElementById('vehicleCountDisplay');
    if (countDisp) countDisp.innerText = json.count;

    if (json.vehicles.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding:2rem; color:var(--text-sub);">No vehicles found matching query.</td></tr>`;
      return;
    }

    tbody.innerHTML = json.vehicles.map(v => {
      const isParked = v.is_currently_parked;
      const statusBadge = isParked 
        ? '<span class="badge badge-occupied">PARKED</span>' 
        : '<span class="badge badge-available">VACATED</span>';

      return `
        <tr>
          <td>
            <a href="/vehicles/${v.plate_number}" style="text-decoration:none;">
              <span class="plate-badge">${v.plate_number}</span>
            </a>
          </td>
          <td><span class="badge badge-ev">${(v.vehicle_type || 'car').toUpperCase()}</span></td>
          <td style="color:var(--text-main); font-weight:600;">${v.owner_name || 'Guest'}</td>
          <td>${v.phone || '--'}</td>
          <td>${statusBadge}</td>
          <td>${isParked ? `<strong style="color:var(--accent-green);">${v.current_slot}</strong>` : '--'}</td>
          <td><strong>${v.total_visits}</strong> visits</td>
          <td style="color:#34d399; font-weight:700;">₹${v.total_paid.toFixed(2)}</td>
          <td>
            <a href="/vehicles/${v.plate_number}" class="btn btn-secondary btn-sm">
              <i class="fa-solid fa-eye"></i> View Dossier
            </a>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Failed to fetch vehicles:', err);
  }
}

// ----------------------------------------------------
// 2. Vehicle Dossier / Details Page
// ----------------------------------------------------
async function loadVehicleDetails(plate) {
  try {
    const res = await fetch(`/api/vehicles/${plate}`);
    const json = await res.json();
    if (!json.success || !json.vehicle) {
      showToast('Could not load vehicle details.', 'error');
      return;
    }

    const v = json.vehicle;

    document.getElementById('vPropType').innerText = (v.vehicle_type || 'car').toUpperCase();
    document.getElementById('vPropOwner').innerText = v.owner_name || 'Guest / Visitor';
    document.getElementById('vPropPhone').innerText = v.phone || 'Not Registered';
    document.getElementById('vPropParked').innerText = v.is_currently_parked ? 'YES' : 'NO';
    document.getElementById('vPropSlot').innerText = v.current_slot || 'None (Outside)';
    document.getElementById('vPropVisits').innerText = `${v.total_visits} Times`;
    document.getElementById('vPropPaid').innerText = `₹${v.total_paid.toFixed(2)}`;

    // Status badge
    const badgeContainer = document.getElementById('vStatusBadgeContainer');
    if (v.is_blacklisted) {
      badgeContainer.innerHTML = `<span class="badge badge-occupied"><i class="fa-solid fa-triangle-exclamation"></i> BLACKLISTED</span>`;
    } else if (v.is_currently_parked) {
      badgeContainer.innerHTML = `<span class="badge badge-occupied"><i class="fa-solid fa-car"></i> CURRENTLY PARKED IN ${v.current_slot}</span>`;
    } else {
      badgeContainer.innerHTML = `<span class="badge badge-available"><i class="fa-solid fa-circle-check"></i> NORMAL STATUS</span>`;
    }

    // Action button
    const actionsBox = document.getElementById('vActionButtons');
    if (v.is_currently_parked) {
      actionsBox.innerHTML = `
        <button class="btn btn-danger" style="width:100%;" onclick="checkoutVehicleFromDossier('${v.plate_number}')">
          <i class="fa-solid fa-arrow-right-from-bracket"></i> Process Vehicle Checkout
        </button>
      `;
    } else {
      actionsBox.innerHTML = `
        <button class="btn btn-primary" style="width:100%;" onclick="checkinVehicleFromDossier('${v.plate_number}', '${v.vehicle_type}')">
          <i class="fa-solid fa-arrow-right-to-bracket"></i> Assign Parking Slot
        </button>
      `;
    }

    // Render history records
    const tbody = document.getElementById('vehicleHistoryTbody');
    if (v.history.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:2rem; color:var(--text-sub);">No parking visits recorded yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = v.history.map(r => `
      <tr>
        <td><strong>${r.slot_number}</strong></td>
        <td>
          <span class="badge ${r.status === 'PARKED' ? 'badge-occupied' : 'badge-available'}">
            ${r.status}
          </span>
        </td>
        <td>${r.entry_time || '--'}</td>
        <td>${r.exit_time || 'Active Session'}</td>
        <td>${r.duration_formatted}</td>
        <td style="color:#34d399; font-weight:700;">₹${r.amount.toFixed(2)}</td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Error loading vehicle dossier:', err);
  }
}

async function checkoutVehicleFromDossier(plate) {
  showToast(`Checking out vehicle ${plate}...`, 'info');
  try {
    const res = await fetch('/api/simulate-exit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plate_number: plate })
    });
    const json = await res.json();
    if (json.success && json.parking_action) {
      showToast(`Checkout complete. Fee: ₹${json.parking_action.amount}`, 'success');
      renderReceipt(json.parking_action);
      loadVehicleDetails(plate);
    }
  } catch (err) {
    showToast('Failed checkout: ' + err.message, 'error');
  }
}

async function checkinVehicleFromDossier(plate, type) {
  showToast(`Checking in vehicle ${plate}...`, 'info');
  try {
    const res = await fetch('/api/vehicle-entry', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plate_number: plate, vehicle_type: type })
    });
    const json = await res.json();
    if (json.success) {
      showToast(`Assigned to ${json.slot_number}`, 'success');
      renderReceipt(json);
      loadVehicleDetails(plate);
    } else {
      showToast(json.message, 'error');
    }
  } catch (err) {
    showToast('Failed check-in: ' + err.message, 'error');
  }
}

// ----------------------------------------------------
// 3. Parking History Table
// ----------------------------------------------------
async function fetchHistory() {
  const search = document.getElementById('historySearchInput')?.value || '';
  const status = document.getElementById('historyStatusFilter')?.value || 'all';

  const tbody = document.getElementById('historyTableBody');
  if (!tbody) return;

  try {
    const res = await fetch(`/api/parking-history?search=${encodeURIComponent(search)}&status=${encodeURIComponent(status)}`);
    const json = await res.json();
    if (!json.success) return;

    const countDisp = document.getElementById('historyCountDisplay');
    if (countDisp) countDisp.innerText = json.count;

    if (json.records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding:2rem; color:var(--text-sub);">No records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = json.records.map(r => {
      const isParked = r.status === 'PARKED';
      const badge = isParked 
        ? '<span class="badge badge-occupied">PARKED</span>' 
        : '<span class="badge badge-available">COMPLETED</span>';

      return `
        <tr>
          <td>#${r.id}</td>
          <td>
            <a href="/vehicles/${r.plate_number}" style="text-decoration:none;">
              <span class="plate-badge">${r.plate_number}</span>
            </a>
          </td>
          <td><strong>${r.slot_number}</strong></td>
          <td>${badge}</td>
          <td>${r.entry_time || '--'}</td>
          <td>${r.exit_time || '<em style="color:var(--text-sub);">Active</em>'}</td>
          <td>${r.duration_formatted}</td>
          <td style="color:${isParked ? 'var(--text-sub)' : '#34d399'}; font-weight:700;">
            ₹${r.amount.toFixed(2)}
          </td>
          <td>
            <button class="btn btn-secondary btn-sm" onclick='renderReceipt(${JSON.stringify(r)})'>
              <i class="fa-solid fa-receipt"></i> View
            </button>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Failed to fetch parking history:', err);
  }
}

// ----------------------------------------------------
// 4. Blacklist Management
// ----------------------------------------------------
async function fetchBlacklist() {
  const tbody = document.getElementById('blacklistTableBody');
  if (!tbody) return;

  try {
    const res = await fetch('/api/blacklist');
    const json = await res.json();
    if (!json.success) return;

    const countBadge = document.getElementById('blCountBadge');
    if (countBadge) countBadge.innerText = `${json.blacklist.length} Flagged`;

    if (json.blacklist.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:2rem; color:var(--text-sub);">No blacklisted vehicles. All entries clear.</td></tr>`;
      return;
    }

    tbody.innerHTML = json.blacklist.map(item => `
      <tr>
        <td><span class="plate-badge" style="background:#fee2e2; border-color:#ef4444; color:#991b1b;">${item.plate_number}</span></td>
        <td style="color:#fca5a5;">${item.reason}</td>
        <td>${item.created_at || '--'}</td>
        <td>
          <button class="btn btn-sm btn-secondary" onclick="removeBlacklistEntry('${item.plate_number}')">
            <i class="fa-solid fa-trash-can" style="color:var(--accent-red);"></i> Remove
          </button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Failed to fetch blacklist:', err);
  }
}

async function submitBlacklistEntry(e) {
  e.preventDefault();
  const plate = document.getElementById('blPlateInput').value.trim().toUpperCase();
  const reason = document.getElementById('blReasonInput').value.trim();

  try {
    const res = await fetch('/api/blacklist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plate_number: plate, reason: reason })
    });
    const json = await res.json();
    if (json.success) {
      showToast(json.message, 'success');
      document.getElementById('blPlateInput').value = '';
      document.getElementById('blReasonInput').value = '';
      fetchBlacklist();
    } else {
      showToast(json.message, 'error');
    }
  } catch (err) {
    showToast('Failed to add to blacklist: ' + err.message, 'error');
  }
}

async function removeBlacklistEntry(plate) {
  if (!confirm(`Are you sure you want to remove vehicle ${plate} from the security blacklist?`)) return;

  try {
    const res = await fetch(`/api/blacklist/${plate}`, { method: 'DELETE' });
    const json = await res.json();
    if (json.success) {
      showToast(json.message, 'success');
      fetchBlacklist();
    } else {
      showToast(json.message, 'error');
    }
  } catch (err) {
    showToast('Failed to remove from blacklist: ' + err.message, 'error');
  }
}

// ----------------------------------------------------
// 5. System Settings
// ----------------------------------------------------
async function loadSystemSettings() {
  try {
    const res = await fetch('/api/settings');
    const json = await res.json();
    if (!json.success || !json.settings) return;

    const s = json.settings;
    if (s.PARKING_FIRST_HOUR_RATE) document.getElementById('settingFirstHour').value = s.PARKING_FIRST_HOUR_RATE;
    if (s.PARKING_ADDITIONAL_HOUR_RATE) document.getElementById('settingAddHour').value = s.PARKING_ADDITIONAL_HOUR_RATE;
    if (s.GRACE_PERIOD_MINUTES) document.getElementById('settingGrace').value = s.GRACE_PERIOD_MINUTES;
    if (s.CURRENCY_SYMBOL) document.getElementById('settingCurrency').value = s.CURRENCY_SYMBOL;
    if (s.PARKING_LOT_NAME) document.getElementById('settingLotName').value = s.PARKING_LOT_NAME;
  } catch (err) {
    console.error('Failed to load settings:', err);
  }
}

async function saveSystemSettings(e) {
  e.preventDefault();
  const form = document.getElementById('settingsForm');
  const formData = new FormData(form);
  const payload = {};
  formData.forEach((val, key) => { payload[key] = val; });

  try {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    if (json.success) {
      showToast('Settings saved successfully.', 'success');
    } else {
      showToast('Failed to save settings.', 'error');
    }
  } catch (err) {
    showToast('Error saving settings: ' + err.message, 'error');
  }
}
