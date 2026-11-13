// Live ANPR Camera & Processing Controller

let currentMode = 'webcam';
let webcamStream = null;
let currentUploadedFile = null;
let selectedVehicleTypePref = 'auto';

// Client-side AI OCR Engine (Tesseract.js WebAssembly - Google OCR)
let clientOcrWorker = null;
let clientOcrReady = false;

async function initClientOCR() {
  if (typeof Tesseract === 'undefined' || clientOcrReady) return;
  try {
    clientOcrWorker = await Tesseract.createWorker('eng');
    await clientOcrWorker.setParameters({
      tessedit_char_whitelist: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ',
      tessedit_pageseg_mode: '7'
    });
    clientOcrReady = true;
    console.log('AI Client OCR (Tesseract.js) initialized.');
  } catch (e) {
    console.warn('Client OCR setup:', e);
  }
}

async function runClientSideOCR(canvas) {
  if (!clientOcrReady || !clientOcrWorker) return null;
  try {
    const cw = canvas.width;
    const ch = canvas.height;
    // Scan central region where plates are shown
    const cropX = Math.round(cw * 0.10);
    const cropY = Math.round(ch * 0.15);
    const cropW = Math.round(cw * 0.80);
    const cropH = Math.round(ch * 0.70);

    const scanCanvas = document.createElement('canvas');
    scanCanvas.width = cropW;
    scanCanvas.height = cropH;
    const sctx = scanCanvas.getContext('2d');
    sctx.drawImage(canvas, cropX, cropY, cropW, cropH, 0, 0, cropW, cropH);

    const ret = await clientOcrWorker.recognize(scanCanvas);
    if (ret && ret.data && ret.data.text) {
      const raw = ret.data.text.replace(/[^A-Za-z0-9]/g, '').toUpperCase();
      // Match Indian standard plate patterns (e.g., AP39CJ5337, TG03A7349, TN09AB1234)
      const m = raw.match(/[A-Z]{2}\d{1,2}[A-Z]{0,3}\d{3,4}/);
      if (m) return m[0];
      if (raw.length >= 7 && /\d{3,4}$/.test(raw)) return raw;
    }
  } catch (err) {
    console.debug('Client OCR pass:', err);
  }
  return null;
}

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

let currentFacingMode = 'environment';

function switchCameraFacing(facing) {
  currentFacingMode = facing;
  const sel = document.getElementById('cameraFacingSelect');
  if (sel) sel.value = facing;
  showToast(`Switching to ${facing === 'environment' ? 'Back/Rear' : 'Front'} Camera...`, 'info');
  startWebcam();
}

function toggleCameraFacing() {
  const next = currentFacingMode === 'environment' ? 'user' : 'environment';
  switchCameraFacing(next);
}

async function startWebcam() {
  const video = document.getElementById('webcamElement');
  const errorBox = document.getElementById('webcamErrorAlert');
  if (errorBox) errorBox.style.display = 'none';

  try {
    if (webcamStream) {
      webcamStream.getTracks().forEach(track => track.stop());
      webcamStream = null;
    }

    const constraints = {
      video: {
        facingMode: { ideal: currentFacingMode },
        width: { ideal: 1280 },
        height: { ideal: 720 }
      },
      audio: false
    };

    try {
      webcamStream = await navigator.mediaDevices.getUserMedia(constraints);
    } catch (e1) {
      try {
        webcamStream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: currentFacingMode },
          audio: false
        });
      } catch (e2) {
        webcamStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      }
    }

    if (video) {
      video.srcObject = webcamStream;
      video.setAttribute('playsinline', '');
      video.setAttribute('autoplay', '');
      video.setAttribute('muted', '');
      await video.play().catch(e => console.log('Autoplay:', e));
    }
    const label = currentFacingMode === 'environment' ? 'Back / Rear Camera' : 'Front Camera';
    showToast(`📷 ${label} Active – Continuous ANPR Live`, 'success');
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

    const clientPlate = await runClientSideOCR(canvas);
    if (clientPlate) {
      formData.append('plate_text', clientPlate);
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

  const action = json.parking_action || {};

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
  if (ownerEl) ownerEl.innerText = json.owner_name || action.owner_name || 'Visitor';

  const modelEl = document.getElementById('vehicleModelText');
  if (modelEl) modelEl.innerText = json.vehicle_model || action.vehicle_model || 'Vehicle';

  document.getElementById('pipelineEngineText').innerText = ocr.engine || 'YOLO + Heuristic OCR';

  // Crop preview
  const cropImg = document.getElementById('plateCropImg');
  const cropPlaceholder = document.getElementById('plateCropPlaceholder');
  if (json.plate_crop_url) {
    cropImg.src = json.plate_crop_url + '?t=' + Date.now();
    cropImg.style.display = 'block';
    cropPlaceholder.style.display = 'none';
  }

  // Multi-frame & sharpness telemetry
  const mf = json.multi_frame || {};
  const mfEl = document.getElementById('multiFrameStatusText');
  if (mfEl) {
    const fCount = mf.frames_aggregated || 1;
    mfEl.innerText = `${fCount} frame${fCount > 1 ? 's' : ''} voted (${mf.sharpness || 0} var)`;
  }

  // Update Live Recognition Stream
  const histEl = document.getElementById('liveRecHistory');
  if (histEl && plateText && plateText !== '-- NO PLATE --') {
    const timeStr = new Date().toLocaleTimeString();
    const item = document.createElement('div');
    item.style.display = 'flex';
    item.style.justifyContent = 'space-between';
    item.style.color = confidence >= 80 ? '#38bdf8' : (confidence >= 60 ? '#f59e0b' : '#ef4444');
    item.innerHTML = `<span>${timeStr} <strong>${plateText}</strong></span><span>${confidence}% (${ocr.engine || 'AI'})</span>`;
    if (histEl.children.length === 1 && histEl.children[0].innerText.includes('Awaiting')) {
      histEl.innerHTML = '';
    }
    histEl.prepend(item);
    if (histEl.children.length > 5) histEl.removeChild(histEl.lastChild);
  }

  // Parking Action Details
  const statusBadge = document.getElementById('statusBadgeAction');
  const slotText = document.getElementById('assignedSlotText');

  if (action && action.action === 'DUPLICATE_SUPPRESSED') {
    statusBadge.className = 'badge badge-ev';
    statusBadge.innerText = 'DUPLICATE SUPPRESSED';
    slotText.innerText = 'ACTIVE IN BAY';
    showToast(action.message, 'info');
  } else if (action && action.action === 'CONFIRM_REQUIRED') {
    statusBadge.className = 'badge badge-reserved';
    statusBadge.innerText = 'CONFIRMATION REQUIRED';
    slotText.innerText = 'OPERATOR CHECK';
    showToast(`Plate ${plateText} detected with ${confidence}% confidence. Please verify.`, 'warning');
  } else if (confidence < 60 || (action && action.action === 'REJECTED_UNCERTAIN')) {
    statusBadge.className = 'badge badge-occupied';
    statusBadge.innerText = 'PLATE RECOGNITION UNCERTAIN - PLEASE VERIFY';
    slotText.innerText = 'UNCERTAIN';
    showToast('PLATE RECOGNITION UNCERTAIN - PLEASE VERIFY', 'warning');
  } else if (action && action.success) {
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

    const clientPlate = await runClientSideOCR(canvas);
    if (clientPlate) {
      formData.append('plate_text', clientPlate);
    }

    try {
      const t0 = Date.now();
      const res = await fetch('/api/anpr/process', { method: 'POST', body: formData });
      const json = await res.json();
      const latency = Date.now() - t0;
      json.latency_ms = latency;

      const latDisp = document.getElementById('latencyDisplay');
      if (latDisp) latDisp.innerText = `${latency} ms`;

      // Update crop preview and telemetry in real time
      if (json.plate_crop_url) {
        const cropImg = document.getElementById('plateCropImg');
        const cropPlaceholder = document.getElementById('plateCropPlaceholder');
        if (cropImg && cropPlaceholder) {
          cropImg.src = json.plate_crop_url + '?t=' + Date.now();
          cropImg.style.display = 'block';
          cropPlaceholder.style.display = 'none';
        }
      }

      const ocr = json.ocr || {};
      const plateText = ocr.cleaned_plate || ocr.raw_text;
      const confidence = Math.round((ocr.confidence || 0) * 100);

      if (plateText) {
        const pDisp = document.getElementById('detectedPlateDisplay');
        if (pDisp) pDisp.innerText = plateText;
        const rDisp = document.getElementById('rawOcrText');
        if (rDisp) rDisp.innerText = ocr.raw_text || plateText;
        const cDisp = document.getElementById('ocrConfidenceText');
        if (cDisp) cDisp.innerText = `${confidence}%`;
        const cBar = document.getElementById('confidenceBar');
        if (cBar) cBar.style.width = `${confidence}%`;
        const engDisp = document.getElementById('pipelineEngineText');
        if (engDisp) engDisp.innerText = ocr.engine || 'AI Multi-Variant';
      }

      // If plate detected and valid (or confident >= 65%)
      if (json.success && ocr && plateText && plateText.length >= 6) {
        const newPlate = ocr.cleaned_plate || plateText;
        if (newPlate !== lastDetectedPlate && (ocr.valid || confidence >= 65)) {
          lastDetectedPlate = newPlate;
          autoScanPaused = true;
          handlePipelineResponse(json);
          setTimeout(() => {
            autoScanPaused = false;
            lastDetectedPlate = null;
          }, 4500);
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
  initClientOCR();
  startWebcam().then(() => startAutoScan());
});
