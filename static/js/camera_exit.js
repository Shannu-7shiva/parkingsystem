// Exit Camera ANPR Controller

let exitCurrentMode = 'webcam';
let exitWebcamStream = null;
let exitUploadFile = null;
let exitAutoScanInterval = null;
let exitLastPlate = null;
let exitAutoScanPaused = false;
let exitIsProcessingFrame = false;
let selectedExitVehicleTypePref = 'auto';

function setExitVehicleTypePref(type) {
  selectedExitVehicleTypePref = type;
  document.querySelectorAll('.btn-exit-vtype').forEach(btn => {
    if (btn.dataset.vtype === type) {
      btn.style.background = '#0284c7';
      btn.style.color = '#fff';
      btn.classList.add('active');
    } else {
      btn.style.background = 'transparent';
      btn.style.color = '#94a3b8';
      btn.classList.remove('active');
    }
  });
  const label = type === 'auto' ? '⚡ AI AUTO-DETECT' : type.toUpperCase();
  showToast(`Exit vehicle mode: ${label}`, 'info');
}

// ----- Webcam -----
async function exitStartWebcam() {
  const video = document.getElementById('exitWebcamElement');
  const errBox = document.getElementById('exitWebcamError');
  if (errBox) errBox.style.display = 'none';

  try {
    if (exitWebcamStream) exitWebcamStream.getTracks().forEach(t => t.stop());

    try {
      exitWebcamStream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false
      });
    } catch (e1) {
      exitWebcamStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    }

    if (video) {
      video.srcObject = exitWebcamStream;
      video.setAttribute('playsinline', '');
      video.setAttribute('autoplay', '');
      video.setAttribute('muted', '');
      await video.play().catch(e => console.log('Autoplay:', e));
    }
    showToast('📷 Exit AI Camera Active – Continuous Auto-Scan Live', 'success');
    exitStartAutoScan();
    return true;
  } catch (err) {
    console.warn('Exit camera initialization failed:', err);
    if (errBox) errBox.style.display = 'block';
    showToast('Exit camera not detected. Use Upload or Simulation mode.', 'warning');
    return false;
  }
}

function exitStopWebcam() {
  if (exitWebcamStream) {
    exitWebcamStream.getTracks().forEach(t => t.stop());
    exitWebcamStream = null;
  }
}

// ----- Auto Scan -----
function exitStartAutoScan() {
  if (exitAutoScanInterval) return;
  exitAutoScanInterval = setInterval(async () => {
    if (exitAutoScanPaused || exitCurrentMode !== 'webcam' || exitIsProcessingFrame) return;
    const video = document.getElementById('exitWebcamElement');
    if (!video || !video.videoWidth || video.paused || video.ended) return;
    await exitCaptureSilent();
  }, 1200);
}

function exitStopAutoScan() {
  if (exitAutoScanInterval) {
    clearInterval(exitAutoScanInterval);
    exitAutoScanInterval = null;
  }
}

async function exitCaptureSilent() {
  const video = document.getElementById('exitWebcamElement');
  const canvas = document.getElementById('exitCaptureCanvas');
  if (!video || !video.videoWidth || !canvas) return;

  exitIsProcessingFrame = true;

  // Ultra-fast scaled frame for sub-second AI inference
  const maxDim = 540;
  let targetW = video.videoWidth;
  let targetH = video.videoHeight;
  if (targetW > maxDim || targetH > maxDim) {
    if (targetW >= targetH) {
      targetH = Math.round((targetH / targetW) * maxDim);
      targetW = maxDim;
    } else {
      targetW = Math.round((targetW / targetH) * maxDim);
      targetH = maxDim;
    }
  }
  canvas.width = targetW;
  canvas.height = targetH;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, targetW, targetH);

  canvas.toBlob(async (blob) => {
    if (!blob) {
      exitIsProcessingFrame = false;
      return;
    }
    const fd = new FormData();
    fd.append('file', blob, 'exit_auto.jpg');
    fd.append('force_action', 'EXIT');
    if (selectedExitVehicleTypePref && selectedExitVehicleTypePref !== 'auto') {
      fd.append('vehicle_type', selectedExitVehicleTypePref);
    }

    try {
      const t0 = Date.now();
      const res = await fetch('/api/anpr/process', { method: 'POST', body: fd });
      const json = await res.json();
      const latency = Date.now() - t0;
      json.latency_ms = latency;

      const latEl = document.getElementById('exitLatencyDisplay');
      if (latEl) latEl.innerText = `${latency} ms`;

      if (json.success && json.ocr && json.ocr.cleaned_plate && json.ocr.cleaned_plate.length >= 5) {
        const plate = json.ocr.cleaned_plate;
        if (plate !== exitLastPlate) {
          exitLastPlate = plate;
          exitAutoScanPaused = true;
          exitHandlePipelineResponse(json);
          setTimeout(() => {
            exitAutoScanPaused = false;
            exitLastPlate = null;
          }, 9000);
        }
      }
    } catch (e) {
      console.debug('Exit auto-scan:', e);
    } finally {
      exitIsProcessingFrame = false;
    }
  }, 'image/jpeg', 0.82);
}

async function exitCaptureAndProcess() {
  const video = document.getElementById('exitWebcamElement');
  const canvas = document.getElementById('exitCaptureCanvas');
  if (!video || !video.videoWidth || !canvas) {
    showToast('Exit camera not active. Switching to simulation mode.', 'warning');
    exitSwitchMode('simulation');
    return;
  }
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);
  canvas.toBlob(async (blob) => {
    if (!blob) return;
    const fd = new FormData();
    fd.append('file', blob, 'exit_capture.jpg');
    fd.append('force_action', 'EXIT');
    if (selectedExitVehicleTypePref && selectedExitVehicleTypePref !== 'auto') {
      fd.append('vehicle_type', selectedExitVehicleTypePref);
    }
    showToast('Processing exit plate...', 'info');
    try {
      const t0 = Date.now();
      const res = await fetch('/api/anpr/process', { method: 'POST', body: fd });
      const json = await res.json();
      json.latency_ms = Date.now() - t0;
      exitHandlePipelineResponse(json);
    } catch (e) {
      showToast('Exit ANPR error: ' + e.message, 'error');
    }
  }, 'image/jpeg', 0.92);
}

// ----- File Upload -----
function exitHandleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  exitUploadFile = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    document.getElementById('exitUploadImg').src = e.target.result;
    document.getElementById('exitUploadPreview').style.display = 'block';
  };
  reader.readAsDataURL(file);
}

async function exitSubmitUpload() {
  if (!exitUploadFile) { showToast('Please select image.', 'warning'); return; }
  const fd = new FormData();
  fd.append('file', exitUploadFile);
  fd.append('force_action', 'EXIT');
  if (selectedExitVehicleTypePref && selectedExitVehicleTypePref !== 'auto') {
    fd.append('vehicle_type', selectedExitVehicleTypePref);
  }
  showToast('Running exit ANPR on uploaded image...', 'info');
  try {
    const res = await fetch('/api/anpr/process', { method: 'POST', body: fd });
    const json = await res.json();
    exitHandlePipelineResponse(json);
  } catch (e) {
    showToast('Error: ' + e.message, 'error');
  }
}

// ----- Simulation -----
async function exitSimulate() {
  showToast('Simulating vehicle exit...', 'info');
  try {
    const res = await fetch('/api/simulate-exit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    const json = await res.json();
    exitHandlePipelineResponse(json);
  } catch (e) {
    showToast('Simulation error: ' + e.message, 'error');
  }
}

async function exitSimulateRandom() {
  showToast('Random demo exit simulation...', 'info');
  try {
    const res = await fetch('/api/auto-demo', { method: 'POST' });
    const json = await res.json();
    exitHandlePipelineResponse(json);
  } catch (e) {
    showToast('Random exit error: ' + e.message, 'error');
  }
}

// ----- Mode Switcher -----
function exitSwitchMode(mode) {
  exitCurrentMode = mode;
  document.getElementById('exitBtnModeWebcam').className = 'btn btn-sm ' + (mode === 'webcam' ? 'btn-primary' : 'btn-secondary');
  document.getElementById('exitBtnModeUpload').className = 'btn btn-sm ' + (mode === 'upload' ? 'btn-primary' : 'btn-secondary');
  document.getElementById('exitBtnModeSim').className = 'btn btn-sm ' + (mode === 'simulation' ? 'btn-primary' : 'btn-secondary');

  document.getElementById('exitWebcamContainer').style.display = mode === 'webcam' ? 'flex' : 'none';
  document.getElementById('exitUploadContainer').style.display = mode === 'upload' ? 'block' : 'none';
  document.getElementById('exitSimContainer').style.display = mode === 'simulation' ? 'block' : 'none';

  const badge = document.getElementById('exitModeBadge');
  if (mode === 'webcam') {
    badge.className = 'badge badge-occupied';
    badge.innerText = 'EXIT GATE: LIVE WEBCAM (AUTO-SCAN)';
    exitStartWebcam();
  } else if (mode === 'upload') {
    badge.className = 'badge badge-vip';
    badge.innerText = 'EXIT GATE: UPLOAD MODE';
    exitStopWebcam(); exitStopAutoScan();
  } else {
    badge.className = 'badge badge-reserved';
    badge.innerText = 'EXIT GATE: SIMULATION';
    exitStopWebcam(); exitStopAutoScan();
  }
}

// ----- Barrier Control -----
let exitBarrierTimeout = null;
function exitSetBarrierStatus(state) {
  const arm = document.getElementById('exitBarrierArm');
  const light = document.getElementById('exitBarrierLight');
  const text = document.getElementById('exitBarrierStatusText');
  if (!arm || !light || !text) return;
  if (exitBarrierTimeout) clearTimeout(exitBarrierTimeout);

  if (state === 'OPEN') {
    arm.style.transform = 'rotate(-72deg)';
    light.style.background = '#22c55e';
    light.style.boxShadow = '0 0 10px #22c55e';
    text.style.color = '#22c55e';
    text.innerHTML = '<i class="fa-solid fa-lock-open"></i> EXIT BARRIER OPEN - PASS';
    playGateSound('chime');
    exitBarrierTimeout = setTimeout(() => exitSetBarrierStatus('CLOSED'), 8000);
  } else {
    arm.style.transform = 'rotate(0deg)';
    light.style.background = '#ef4444';
    light.style.boxShadow = '0 0 6px #ef4444';
    text.style.color = '#ef4444';
    text.innerHTML = '<i class="fa-solid fa-lock"></i> BARRIER CLOSED';
  }
}

// ----- Manual Override -----
async function exitManualOverride() {
  const plate = document.getElementById('exitManualPlate').value.trim().toUpperCase();
  if (!plate) { showToast('Enter a license plate number.', 'warning'); return; }
  showToast('Processing manual exit: ' + plate, 'info');
  try {
    const vType = selectedExitVehicleTypePref && selectedExitVehicleTypePref !== 'auto' ? selectedExitVehicleTypePref : 'motorcycle';
    const res = await fetch('/api/vehicle-exit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plate_number: plate, vehicle_type: vType, payment_mode: 'UPI / Online' })
    });
    const json = await res.json();
    if (json.success) {
      exitHandlePipelineResponse({
        success: true,
        vehicle_type: json.vehicle_type || 'car',
        ocr: { cleaned_plate: plate, raw_text: plate, confidence: 1.0, engine: 'Manual Input' },
        parking_action: json,
        latency_ms: 0
      });
    } else {
      showToast(json.message || 'Exit could not be processed', 'error');
    }
  } catch (e) {
    showToast('Error: ' + e.message, 'error');
  }
}

// ----- Pipeline Response Handler -----
function exitHandlePipelineResponse(json) {
  if (!json) return;

  // Handle simulated exit response (direct from /api/simulate-exit or pipeline)
  const action = json.parking_action || (json.action ? json : null);

  // Latency
  const latEl = document.getElementById('exitLatencyDisplay');
  if (latEl && json.latency_ms !== undefined) latEl.innerText = json.latency_ms + ' ms';

  if (!json.success && !action) {
    showToast(json.message || json.error || 'Failed to process exit.', 'error');
    return;
  }

  // OCR results
  if (json.ocr) {
    const plate = json.ocr.cleaned_plate || json.ocr.raw_text || '--';
    const plateDisp = document.getElementById('exitPlateDisplay');
    if (plateDisp) plateDisp.innerText = plate || '-- NO PLATE --';

    // Plate crop
    const cropImg = document.getElementById('exitPlateCrop');
    const cropPlace = document.getElementById('exitCropPlaceholder');
    if (json.plate_crop_url && cropImg && cropPlace) {
      cropImg.src = json.plate_crop_url + '?t=' + Date.now();
      cropImg.style.display = 'block';
      cropPlace.style.display = 'none';
    }
    const vtEl = document.getElementById('exitVehicleType');
    if (vtEl) vtEl.innerText = (json.vehicle_type || 'car').toUpperCase() + ' ' + (typeof getVehicleIcon === 'function' ? getVehicleIcon(json.vehicle_type) : '');
    const ownerEl = document.getElementById('exitOwnerName');
    if (ownerEl) ownerEl.innerText = json.owner_name || (action && action.owner_name) || 'Visitor';
    const modelEl = document.getElementById('exitVehicleModel');
    if (modelEl) modelEl.innerText = json.vehicle_model || (action && action.vehicle_model) || 'Vehicle';
  }

  // Parking action
  if (action && action.success) {
    const pa = action.parking_action || action;
    const statusBadge = document.getElementById('exitStatusBadge');

    if ((pa.action === 'EXIT') || pa.status === 'COMPLETED' || (pa.amount !== undefined && pa.amount >= 0)) {
      if (statusBadge) {
        statusBadge.className = 'badge badge-occupied';
        statusBadge.innerText = 'EXIT PROCESSED';
      }
      const entryTimeEl = document.getElementById('exitEntryTime');
      const durEl = document.getElementById('exitDuration');
      const amtEl = document.getElementById('exitAmount');
      if (entryTimeEl) entryTimeEl.innerText = pa.entry_time || '--';
      if (durEl) durEl.innerText = pa.formatted_duration || pa.duration_formatted || '--';
      if (amtEl) amtEl.innerText = '₹' + (pa.amount || 0).toFixed(2);
      exitSetBarrierStatus('OPEN');
      renderExitBill(pa);
      if (typeof renderReceipt === 'function') renderReceipt(pa);
      showToast(`✅ Exit: ${pa.plate_number} | Duration: ${pa.formatted_duration || pa.duration_formatted} | Bill: ₹${pa.amount}`, 'success');
    } else if (pa.action === 'ENTRY') {
      showToast(`Vehicle ${pa.plate_number} has not completed parking yet.`, 'info');
      if (typeof renderReceipt === 'function') renderReceipt(pa);
    }
  } else if (action && !json.success) {
    showToast(json.message || 'No active parking session found for this vehicle.', 'warning');
  }
}

function renderExitBill(data) {
  const card = document.getElementById('exitBillDetails');
  const statusEl = document.getElementById('exitBillStatus');
  if (!card) return;
  if (statusEl) {
    statusEl.className = 'badge badge-available';
    statusEl.innerText = 'BILL GENERATED';
  }

  const total = (data.amount || 0).toFixed(2);
  const base = (data.base_amount || (data.amount / 1.18) || 0).toFixed(2);
  const gst = (data.gst_amount || (data.amount - data.amount / 1.18) || 0).toFixed(2);
  const recNo = data.receipt_id || data.receipt_number || 'REC-EXIT';
  const vType = (data.vehicle_type || 'car').toUpperCase();
  const vIcon = typeof getVehicleIcon === 'function' ? getVehicleIcon(data.vehicle_type) : '🚗';

  card.innerHTML = `
    <div style="text-align:center; margin-bottom:1rem; padding-bottom:1rem; border-bottom:1px dashed var(--border-color);">
      <div style="font-size:0.75rem; color:var(--text-sub); text-transform:uppercase;">Total Amount Due</div>
      <div style="font-size:2.4rem; font-weight:900; color:#22c55e;">₹${total}</div>
      <div style="font-size:0.8rem; color:var(--text-muted);">Receipt: ${recNo}</div>
    </div>
    <div style="display:flex; flex-direction:column; gap:0.4rem; font-size:0.84rem;">
      <div style="display:flex; justify-content:space-between;"><span>Vehicle:</span><strong style="color:var(--accent-cyan);">${vIcon} ${vType}</strong></div>
      <div style="display:flex; justify-content:space-between;"><span>License Plate:</span><strong>${data.plate_number}</strong></div>
      <div style="display:flex; justify-content:space-between;"><span>Assigned Bay:</span><strong>${data.slot_number}</strong></div>
      <div style="display:flex; justify-content:space-between;"><span>Total Duration:</span><strong style="color:var(--accent-amber);">${data.formatted_duration || data.duration_formatted || '--'}</strong></div>
      <div style="display:flex; justify-content:space-between;"><span>Taxable Subtotal:</span><span>₹${base}</span></div>
      <div style="display:flex; justify-content:space-between;"><span>GST (18%):</span><span>₹${gst}</span></div>
      <div style="display:flex; justify-content:space-between; font-weight:700; color:#22c55e; border-top:1px dashed var(--border-color); padding-top:0.5rem; margin-top:0.25rem;"><span>Total Bill:</span><span>₹${total}</span></div>
    </div>
    <div style="margin-top:1rem; display:flex; gap:0.5rem; flex-wrap:wrap; justify-content:center;">
      <button class="btn btn-sm" style="background:#166534; color:#fff;" onclick="showPaymentModal()">
        <i class="fa-solid fa-credit-card"></i> Pay Now (UPI / Fastag / Card / Cash)
      </button>
      <button class="btn btn-sm btn-secondary" onclick="printReceiptSlip()">
        <i class="fa-solid fa-print"></i> Print Bill Slip
      </button>
    </div>
  `;

  // Set payNowBtn amount for payment modal
  const payBtn = document.getElementById('payNowBtn');
  if (payBtn) {
    payBtn.dataset.amount = data.amount || 0;
    payBtn.style.display = 'inline-flex';
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  exitStartWebcam();
});

