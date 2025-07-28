// app.js - Final Corrected Version

// Configuration
const API_BASE_URL = "http://localhost:8095"; 
const REFRESH_INTERVAL = 5000; // 5 seconds

// DOM Elements
const houseGrid = document.getElementById('house-grid');
const themeToggleButton = document.getElementById('theme-toggle');
const refreshTimerDiv = document.getElementById('refresh-timer');

/**
 * Fetches the latest data from the Operator Control API.
 */
async function fetchData() {
    try {
        const response = await fetch(`${API_BASE_URL}/houses`);
        if (!response.ok) {
            throw new Error(`API request failed with status ${response.status}`);
        }
        const housesData = await response.json();

        const alertsResponse = await fetch(`${API_BASE_URL}/motion_alerts`);
        const alertsData = await alertsResponse.json();
        
        return { houses: housesData, motion_alerts: alertsData.activeAlerts || [] };
    } catch (error) {
        console.error("Failed to fetch data:", error);
        houseGrid.innerHTML = `
            <div class="col-12">
                <div class="alert alert-danger" role="alert">
                    <h4 class="alert-heading"><i class="bi bi-exclamation-triangle-fill"></i> Connection Error!</h4>
                    <p>Could not connect to the Operator Control service at <strong>${API_BASE_URL}</strong>.</p>
                    <hr>
                    <p class="mb-0">Please ensure the backend services are running and accessible.</p>
                </div>
            </div>`;
        return null;
    }
}

/**
 * Renders the entire dashboard with the latest data.
 */
function renderDashboard(data) {
    if (!data) return;
    renderGlobalAlert(data);

    houseGrid.innerHTML = ''; // Clear the grid

    if (Object.keys(data.houses).length === 0) {
        houseGrid.innerHTML = `<p class="text-muted">No houses found or available.</p>`;
        return;
    }

    for (const houseId in data.houses) {
        const house = data.houses[houseId];
        if (house) { // Ensure house object is not null
            const houseCard = createHouseCard(house, data.motion_alerts);
            houseGrid.appendChild(houseCard);
        }
    }
}

/**
 * Renders a global "THIEF DETECTED!" alert.
 */
function renderGlobalAlert(data) {
    const alertContainer = document.getElementById('global-alert-container');
    const motionAlerts = data.motion_alerts;

    if (motionAlerts && motionAlerts.length > 0) {
        const alertDetails = motionAlerts.map(alertKey => {
            const [houseID, floorID, unitID] = alertKey.split('-');
            return `House ${houseID}, Floor ${floorID}, Unit ${unitID}`;
        }).join('; ');

        alertContainer.innerHTML = `
            <div class="alert alert-danger d-flex align-items-center shadow-lg" role="alert">
                <i class="bi bi-exclamation-triangle-fill fs-2 me-3"></i>
                <div>
                    <h4 class="alert-heading">THIEF DETECTED!</h4>
                    <p class="mb-0">
                        Immediate motion detected in the following location(s): <strong>${alertDetails}</strong>.
                    </p>
                </div>
            </div>`;
    } else {
        alertContainer.innerHTML = '';
    }
}

/**
 * Creates an HTML card element for a single house.
 */
function createHouseCard(house, motionAlerts) {
    const isBreached = house.floors.some(floor => 
        floor.units.some(unit => motionAlerts.includes(`${house.houseID}-${floor.floorID}-${unit.unitID}`))
    );

    const card = document.createElement('div');
    card.className = 'col';
    
    let cardBodyHtml = '';
    
    house.floors.forEach(floor => {
        floor.units.forEach(unit => {
            cardBodyHtml += `<h6 class="mt-3 text-muted">F${floor.floorID}/U${unit.unitID}</h6>`;
            
            if (unit.devicesList && unit.devicesList.length > 0) {
                cardBodyHtml += '<ul class="list-group list-group-flush">';
                unit.devicesList.forEach(device => {
                    const icon = getDeviceIcon(device.deviceName, device.deviceStatus);
                    const statusClass = (device.deviceStatus || 'unknown').toLowerCase().replace(' ', '-');
                    const badgeColor = getStatusBadgeColor(device.deviceStatus);
                    
                    const unitKey = `${house.houseID}-${floor.floorID}-${unit.unitID}`;
                    const isAlerting = motionAlerts.includes(unitKey) && device.deviceName.includes('motion');
                    const alertClass = isAlerting ? 'list-group-item-danger' : '';

                    let descriptionHtml = `<small class="text-muted d-block">Last Update: ${new Date(device.lastUpdate).toLocaleTimeString()}</small>`;
                    
                    if (device.deviceName.includes('light_sensor') && device.value !== undefined) {
                        descriptionHtml += `<small class="text-muted d-block">Light Level: <strong>${device.value} lux</strong></small>`;
                    }

                    if (device.deviceName.includes('light_switch') && device.deviceStatus === 'ON') {
                        const reason = motionAlerts.includes(unitKey) ? 'Motion Detected' : 'Manual';
                        descriptionHtml += `<small class="text-info d-block">Reason: <strong>${reason}</strong></small>`;
                    }

                    cardBodyHtml += `
                        <li class="list-group-item d-flex justify-content-between align-items-center ${alertClass}">
                            <div>
                                <i class="bi ${icon} me-2"></i>
                                <strong>${device.deviceName.replace(/_/g, ' ')}</strong>
                                ${descriptionHtml}
                            </div>
                            <span class="badge ${badgeColor} status-badge ${statusClass}">${device.deviceStatus}</span>
                        </li>`;
                });
                cardBodyHtml += '</ul>';
            } else {
                cardBodyHtml += '<p class="text-muted small">No devices in this unit.</p>';
            }
        });
    });

    const thingspeakLink = getThingSpeakLink(house.houseID);

    card.innerHTML = `
        <div class="card h-100 shadow-sm">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0">
                    <i class="bi bi-house-door-fill me-2"></i>${house.houseName}
                </h5>
                <span class="badge rounded-pill ${isBreached ? 'bg-danger security-status breach' : 'bg-success security-status'}">
                    <i class="bi ${isBreached ? 'bi-exclamation-shield-fill' : 'bi-shield-check'} me-1"></i>
                    ${isBreached ? 'BREACH' : 'SECURE'}
                </span>
            </div>
            <div class="card-body">${cardBodyHtml}</div>
            <div class="card-footer bg-transparent border-top-0">
                <a href="${thingspeakLink}" class="btn btn-outline-primary btn-sm w-100" target="_blank">
                    <i class="bi bi-graph-up-arrow me-2"></i>View ThingSpeak Chart
                </a>
            </div>
        </div>`;
    return card;
}

// =======================================================
// HELPER FUNCTIONS (THESE WERE MISSING)
// =======================================================
function getDeviceIcon(deviceName, deviceStatus) {
    if (deviceName.includes('light_sensor')) return 'bi-brightness-high-fill';
    if (deviceName.includes('light_switch')) return deviceStatus === 'ON' ? 'bi-lightbulb-fill' : 'bi-lightbulb-off';
    if (deviceName.includes('motion_sensor')) return 'bi-person-walking';
    return 'bi-hdd';
}

function getStatusBadgeColor(status) {
    switch (status) {
        case 'ON': return 'bg-success';
        case 'OFF': return 'bg-secondary';
        case 'Detected': return 'bg-warning text-dark';
        case 'No Motion': return 'bg-info text-dark';
        case 'DISABLE': return 'bg-dark';
        default: return 'bg-light text-dark';
    }
}

function getThingSpeakLink(houseId) {
    const channelMap = { '1': '2884625', '2': '2884626' }; 
    const channelId = channelMap[houseId];
    return channelId ? `https://thingspeak.com/channels/${channelId}` : '#';
}
// =======================================================

// --- Theme Toggler ---
themeToggleButton.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-bs-theme');
    if (currentTheme === 'dark') {
        document.documentElement.setAttribute('data-bs-theme', 'light');
        themeToggleButton.innerHTML = '<i class="bi bi-moon-stars-fill"></i>';
    } else {
        document.documentElement.setAttribute('data-bs-theme', 'dark');
        themeToggleButton.innerHTML = '<i class="bi bi-sun-fill"></i>';
    }
});

// --- Main Application Logic ---
async function main() {
    const data = await fetchData();
    renderDashboard(data);
}

main();
setInterval(main, REFRESH_INTERVAL);

let countdown = REFRESH_INTERVAL / 1000;
setInterval(() => {
    countdown = countdown > 1 ? countdown - 1 : REFRESH_INTERVAL / 1000;
    refreshTimerDiv.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Refreshing in ${countdown}s`;
}, 1000);