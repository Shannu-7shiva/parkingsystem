// Analytics and Chart.js Controller

let vehicleChartInstance = null;
let revenueChartInstance = null;
let peakHoursChartInstance = null;
let vehicleTypeChartInstance = null;

async function loadAnalyticsData() {
  try {
    const res = await fetch('/api/analytics');
    const json = await res.json();
    if (!json.success || !json.data) return;

    const data = json.data;

    // 1. Update KPI Summary Cards
    document.getElementById('kpiTotalVehicles').innerText = data.total_vehicles_all_time;
    document.getElementById('kpiTotalRevenue').innerText = `₹${data.total_revenue_all_time.toFixed(2)}`;
    document.getElementById('kpiAvgDuration').innerText = `${data.average_duration_minutes} mins`;
    document.getElementById('kpiOccupancyPct').innerText = `${data.occupancy_percentage}%`;

    // 2. Render Charts
    renderVehicleChart(data.chart_labels, data.daily_vehicle_counts);
    renderRevenueChart(data.chart_labels, data.daily_revenue);
    renderPeakHoursChart(data.peak_hours);
    renderVehicleTypeChart(data.vehicle_types);
  } catch (err) {
    console.error('Error loading analytics:', err);
  }
}

function renderVehicleChart(labels, counts) {
  const ctx = document.getElementById('chartDailyVehicles').getContext('2d');
  if (vehicleChartInstance) vehicleChartInstance.destroy();

  vehicleChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Vehicles Processed',
        data: counts,
        backgroundColor: 'rgba(0, 240, 255, 0.65)',
        borderColor: '#00f0ff',
        borderWidth: 1.5,
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#9ca3af' } },
        y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#9ca3af', stepSize: 1 }, beginAtZero: true }
      }
    }
  });
}

function renderRevenueChart(labels, revenues) {
  const ctx = document.getElementById('chartDailyRevenue').getContext('2d');
  if (revenueChartInstance) revenueChartInstance.destroy();

  revenueChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Revenue (₹)',
        data: revenues,
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.15)',
        borderWidth: 2.5,
        fill: true,
        tension: 0.35,
        pointBackgroundColor: '#10b981',
        pointRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#9ca3af' } },
        y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#9ca3af' }, beginAtZero: true }
      }
    }
  });
}

function renderPeakHoursChart(hourlyCounts) {
  const ctx = document.getElementById('chartPeakHours').getContext('2d');
  if (peakHoursChartInstance) peakHoursChartInstance.destroy();

  const labels = Array.from({ length: 24 }, (_, i) => `${i.toString().padStart(2, '0')}:00`);

  peakHoursChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Arrivals per Hour',
        data: hourlyCounts,
        borderColor: '#f59e0b',
        backgroundColor: 'rgba(245, 158, 11, 0.15)',
        borderWidth: 2,
        fill: true,
        tension: 0.3,
        pointRadius: 3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(255, 255, 255, 0.03)' }, ticks: { color: '#9ca3af', maxTicksLimit: 12 } },
        y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#9ca3af', stepSize: 1 }, beginAtZero: true }
      }
    }
  });
}

function renderVehicleTypeChart(typesDict) {
  const ctx = document.getElementById('chartVehicleTypes').getContext('2d');
  if (vehicleTypeChartInstance) vehicleTypeChartInstance.destroy();

  const labels = ['Cars', 'Motorcycles', 'Buses', 'Trucks', 'Electric EVs'];
  const data = [
    typesDict.car || 0,
    typesDict.motorcycle || 0,
    typesDict.bus || 0,
    typesDict.truck || 0,
    typesDict.ev || 0
  ];

  vehicleTypeChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: ['#3b82f6', '#f59e0b', '#ec4899', '#8b5cf6', '#06b6d4'],
        borderWidth: 2,
        borderColor: '#111827'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: { color: '#d1d5db', font: { size: 12 } }
        }
      }
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  loadAnalyticsData();
});
