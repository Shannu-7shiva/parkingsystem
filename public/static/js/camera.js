// Live ANPR Camera & Processing Controller

let currentMode = 'webcam';
let webcamStream = null;
let currentUploadedFile = null;
let selectedVehicleTypePref = 'auto';

function setVehicleTypePref(type) {
  selectedVehicleTypePref = type;
  document.querySelectorAll('.btn-vtype').forEach(btn => {
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
  showToast(`Vehicle mode: ${label}`, 'info');
}

function switchMode(mode) {
  currentMode = mode;

  // Reset buttons
  document.getElementById('btnModeWebcam').className = 'btn btn-sm ' + (mode === 'webcam' ? 'btn-primary' : 'btn-secondary');
  document.getElementById('btnModeUpload').className = 'btn btn-sm ' + (mode === 'upload' ? 'btn-primary' : 'btn-secondary');
  document.getElementById('btnModeSim').className = 'btn btn-sm ' + (mode === 'simulation' ? 'btn-primary' : 'btn-secondary');

  // Containers
  document.getElementById('webcamContainer').style.display = (mode === 'webcam') ? 'flex' : 'none';
  document.getElementById('uploadContainer').style.display = (mode === 'upload') ? 'block' : 'none';
  document.getElementById('simulationContainer').style.display = (mode === 'simulation') ? 'block' : 'none';

  // Badge (Requirement 37)
  const badge = document.getElementById('modeBadge');
  if (mode === 'webcam') {
    badge.className = 'badge badge-ev';
    badge.innerText = 'REAL ANPR: LIVE WEBCAM (AUTO-SCAN)';
    startWebcam().then(() => startAutoScan());
  } else if (mode === 'upload') {
    badge.className = 'badge badge-vip';
    badge.innerText = 'REAL ANPR: UPLOAD MEDIA';
    stopWebcam();
    stopAutoScan();
  } else {
    badge.className = 'badge badge-reserved';
    badge.innerText = 'DEMO SIMULATION MODE';
    stopWebcam();
    stopAutoScan();
    loadLatestSimFrame();
  }
}

async function startWebcam() {
  const video = document.getElementById('webcamElement');
  const errorBox = document.getElementById('webcamErrorAlert');
  if (errorBox) errorBox.style.display = 'none';

  try {
    if (webcamStream) {
      webcamStream.getTracks().forEach(track => track.stop());
    }

    try {
      webcamStream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false
      });
    } catch (e1) {
      webcamStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    }

    if (video) {
      video.srcObject = webcamStream;
      video.setAttribute('playsinline', '');
      video.setAttribute('autoplay', '');
      video.setAttribute('muted', '');
      await video.play().catch(e => console.log('Autoplay:', e));
    }
    showToast('📷 Entry AI Camera Active – Continuous Auto-Scan Live', 'success');
    startAutoScan();
    return true;
  } catch (err) {
    console.warn('Webcam initialization failed:', err);
    if (errorBox) errorBox.style.display = 'block';
    showToast('Camera not detected. You can use Simulation or Upload mode.', 'warning');
    return false;
  }
}

function stopWebcam() {
  if (webcamStream) {
    webcamStream.getTracks().forEach(track => track.stop());
    webcamStream = null;
  }
}

async function captureAndProcessFrame() {
  const video = document.getElementById('webcamElement');
  const canvas = document.getElementById('captureCanvas');

  if (!video.videoWidth) {
    showToast('Camera stream is not active. Switching to simulation mode.', 'warning');
    switchMode('simulation');
    return;
  }

  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  canvas.toBlob(async (blob) => {
    if (!blob) return;
    const formData = new FormData();
    formData.append('file', blob, 'webcam_capture.jpg');
    if (selectedVehicleTypePref && selectedVehicleTypePref !== 'auto') {
      formData.append('vehicle_type', selectedVehicleTypePref);
    }

    showToast('Processing frame through ANPR pipeline...', 'info');
    try {
      const res = await fetch('/api/anpr/process', { method: 'POST', body: formData });
      const json = await res.json();
      handlePipelineResponse(json);
    } catch (err) {
      showToast('ANPR request failed: ' + err.message, 'error');
    }
  }, 'image/jpeg', 0.92);
}

function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  currentUploadedFile = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    document.getElementById('uploadPreviewImg').src = e.target.result;
    document.getElementById('uploadPreviewBox').style.display = 'block';
  };
  reader.readAsDataURL(file);
}

async function submitUploadedImage() {
  if (!currentUploadedFile) {
    showToast('Please select an image file first.', 'warning');
    return;
  }

  const formData = new FormData();
  formData.append('file', currentUploadedFile);
  if (selectedVehicleTypePref && selectedVehicleTypePref !== 'auto') {
    formData.append('vehicle_type', selectedVehicleTypePref);
  }

  showToast('Running ANPR pipeline on uploaded media...', 'info');
  try {
    const res = await fetch('/api/anpr/process', { method: 'POST', body: formData });
    const json = await res.json();
    handlePipelineResponse(json);
  } catch (err) {
    showToast('Error processing media: ' + err.message, 'error');
  }
}

async function triggerSimEvent(type) {
  showToast(`Simulating ${type}...`, 'info');

  try {
    let url = '/api/simulate-entry';
    let payload = {};

    if (type === 'EXIT') {
      url = '/api/simulate-exit';
    } else if (type === 'RANDOM') {
      url = '/api/auto-demo';
    }

    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    handlePipelineResponse(json);

    if (json.annotated_image_url) {
      document.getElementById('simFramePreview').src = json.annotated_image_url + '?t=' + Date.now();
    }
  } catch (err) {
    showToast('Simulation error: ' + err.message, 'error');
  }
}

let barrierTimeout = null;
function setBarrierStatus(state) {
  const arm = document.getElementById('barrierArm');
  const light = document.getElementById('barrierLight');
  const text = document.getElementById('barrierStatusText');
  if (!arm || !light || !text) return;

  if (barrierTimeout) clearTimeout(barrierTimeout);

  if (state === 'OPEN') {
    arm.style.transform = 'rotate(-72deg)';
    light.style.background = '#22c55e';
    light.style.boxShadow = '0 0 10px #22c55e';
    text.style.color = '#22c55e';
    text.innerHTML = '<i class="fa-solid fa-lock-open"></i> BARRIER OPEN - PASS';

    // Auto-close after 6 seconds
    barrierTimeout = setTimeout(() => {
      setBarrierStatus('CLOSED');
    }, 6000);
  } else if (state === 'LOCKED') {
    arm.style.transform = 'rotate(0deg)';
    light.style.background = '#dc2626';
    light.style.boxShadow = '0 0 14px #dc2626';
    text.style.color = '#dc2626';
    text.innerHTML = '<i class="fa-solid fa-ban"></i> BARRIER LOCKED - BLOCKED';
  } else {
    // CLOSED
    arm.style.transform = 'rotate(0deg)';
    light.style.background = '#ef4444';
    light.style.boxShadow = '0 0 6px #ef4444';
    text.style.color = '#ef4444';
    text.innerHTML = '<i class="fa-solid fa-lock"></i> BARRIER CLOSED';
  }
}

function handlePipelineResponse(json) {
  if (!json.success) {
    showToast(json.message || json.error || 'Failed to extract number plate.', 'error');
    return;
  }

  // Update Latency
  const latDisp = document.getElementById('latencyDisplay');
  if (latDisp && json.latency_ms !== undefined) {
    latDisp.innerText = `${json.latency_ms} ms`;
  }

  // Update UI Telemetry
  const ocr = json.ocr || {};
  const plateText = ocr.cleaned_plate || ocr.raw_text || '-- NO PLATE --';
  const confidence = Math.round((ocr.confidence || 0) * 100);

  document.getElementById('detectedPlateDisplay').innerText = plateText;
  document.getElementById('rawOcrText').innerText = ocr.raw_text || 'None';
  document.getElementById('ocrConfidenceText').innerText = `${confidence}%`;
  document.getElementById('confidenceBar').style.width = `${confidence}%`;
  document.getElementById('detectedVehicleType').innerText = (json.vehicle_type || 'Car').toUpperCase() + (typeof getVehicleIcon === 'function' ? ' ' + getVehicleIcon(json.vehicle_type) : '');
  
  const ownerEl = document.getElementById('ownerNameText');
  if (ownerEl) ownerEl.innerText = json.owner_name || (action && action.owner_name) || 'Visitor';

  const modelEl = document.getElementById('vehicleModelText');
  if (modelEl) modelEl.innerText = json.vehicle_model || (action && action.vehicle_model) || 'Vehicle';

  document.getElementById('pipelineEngineText').innerText = ocr.engine || 'YOLO + Heuristic OCR';

  // Crop preview
  const cropImg = document.getElementById('plateCropImg');
  const cropPlaceholder = document.getElementById('plateCropPlaceholder');
  if (json.plate_crop_url) {
    cropImg.src = json.plate_crop_url + '?t=' + Date.now();
    cropImg.style.display = 'block';
    cropPlaceholder.style.display = 'none';
  }

  // Parking Action Details
  const action = json.parking_action;
  const statusBadge = document.getElementById('statusBadgeAction');
  const slotText = document.getElementById('assignedSlotText');

  if (action && action.success) {
    if (action.action === 'ENTRY') {
      statusBadge.className = 'badge badge-available';
      statusBadge.innerText = 'ENTRY DETECTED';
      slotText.innerText = action.slot_number || '--';
      setBarrierStatus('OPEN');
      showToast(`Plate Verified: ${action.plate_number} -> Assigned to Bay ${action.slot_number}`, 'success');
      renderReceipt(action);
    } else if (action.action === 'EXIT') {
      statusBadge.className = 'badge badge-occupied';
      statusBadge.innerText = 'EXIT DETECTED';
      slotText.innerText = `Vacated ${action.slot_number}`;
      setBarrierStatus('OPEN');
      showToast(`Exit Verified: ${action.plate_number}. Amount: ₹${action.amount}`, 'success');
      renderReceipt(action);
    }
  } else if (action && action.blacklisted) {
    statusBadge.className = 'badge badge-occupied';
    statusBadge.innerText = 'BLACKLIST ALERT';
    slotText.innerText = 'ENTRY DENIED';
    setBarrierStatus('LOCKED');
    renderReceipt(action);
  } else {
    statusBadge.className = 'badge badge-reserved';
    statusBadge.innerText = 'PLATE IDENTIFIED';
    slotText.innerText = action ? (action.slot_number || 'Awaiting Action') : '--';
  }
}

async function submitManualPlateOverride() {
  const plate = document.getElementById('manualPlateInput').value.trim().toUpperCase();
  if (!plate) {
    showToast('Please type a valid license plate number.', 'warning');
    return;
  }

  showToast(`Processing manual plate override: ${plate}...`, 'info');
  try {
    const res = await fetch('/api/vehicle-entry', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plate_number: plate, vehicle_type: 'car' })
    });
    const json = await res.json();
    if (json.success) {
      handlePipelineResponse({
        success: true,
        vehicle_type: 'car',
        ocr: { cleaned_plate: plate, raw_text: plate, confidence: 1.0, engine: 'Manual Input' },
        parking_action: json
      });
    } else {
      showToast(json.message, 'error');
    }
  } catch (err) {
    showToast('Failed to apply manual plate: ' + err.message, 'error');
  }
}

async function loadLatestSimFrame() {
  try {
    const res = await fetch('/api/simulate-entry', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plate_number: 'TN09AB1234' })
    });
    const json = await res.json();
    handlePipelineResponse(json);
    if (json.annotated_image_url) {
      document.getElementById('simFramePreview').src = json.annotated_image_url + '?t=' + Date.now();
    }
  } catch (err) {
    console.error('Error loading sim frame:', err);
  }
}

// Auto-scan state
let autoScanInterval = null;
let lastDetectedPlate = null;
let autoScanPaused = false;
let isProcessingFrame = false;

function startAutoScan() {
  if (autoScanInterval) return;
  autoScanInterval = setInterval(async () => {
    if (autoScanPaused || currentMode !== 'webcam' || isProcessingFrame) return;
    const video = document.getElementById('webcamElement');
    if (!video || !video.videoWidth || video.paused || video.ended) return;
    await captureAndProcessFrameSilent();
  }, 1200);
}

function stopAutoScan() {
  if (autoScanInterval) {
    clearInterval(autoScanInterval);
    autoScanInterval = null;
  }
}

async function captureAndProcessFrameSilent() {
  const video = document.getElementById('webcamElement');
  const canvas = document.getElementById('captureCanvas');
  if (!video || !video.videoWidth || !canvas) return;

  isProcessingFrame = true;

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
      isProcessingFrame = false;
      return;
    }
    const formData = new FormData();
    formData.append('file', blob, 'webcam_entry_auto.jpg');
    formData.append('force_action', 'ENTRY');
    if (selectedVehicleTypePref && selectedVehicleTypePref !== 'auto') {
      formData.append('vehicle_type', selectedVehicleTypePref);
    }

    try {
      const t0 = Date.now();
      const res = await fetch('/api/anpr/process', { method: 'POST', body: formData });
      const json = await res.json();
      const latency = Date.now() - t0;
      json.latency_ms = latency;

      const latDisp = document.getElementById('latencyDisplay');
      if (latDisp) latDisp.innerText = `${latency} ms`;

      // If plate detected and valid
      if (json.success && json.ocr && json.ocr.cleaned_plate && json.ocr.cleaned_plate.length >= 5) {
        const newPlate = json.ocr.cleaned_plate;
        if (newPlate !== lastDetectedPlate) {
          lastDetectedPlate = newPlate;
          autoScanPaused = true; // Pause to display ticket and allow vehicle through
          handlePipelineResponse(json);
          setTimeout(() => {
            autoScanPaused = false;
            lastDetectedPlate = null;
          }, 9000);
        }
      }
    } catch (err) {
      console.debug('Auto-scan:', err);
    } finally {
      isProcessingFrame = false;
    }
  }, 'image/jpeg', 0.82);
}

// Start webcam and auto-scan when page loads
document.addEventListener('DOMContentLoaded', () => {
  startWebcam().then(() => startAutoScan());
});
