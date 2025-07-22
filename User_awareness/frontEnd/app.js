// app.js - Modern JavaScript for the ThiefDetector Dashboard (v2)

// Configuration
const API_BASE_URL = "http://127.0.0.1:8095";
const REFRESH_INTERVAL = 5000; // 5 seconds

// DOM Elements
const houseGrid = document.getElementById('house-grid');
const themeToggleButton = document.getElementById('theme-toggle');
const refreshTimerDiv = document.getElementById('refresh-timer');

/**
 * Fetches the latest data from the Operator Control API.
 * @returns {Promise<object>} The API response data.
 */
async function fetchData() {
    try {
        const response = await fetch(`${API_BASE_URL}/houses`);
        if (!response.ok) {
            throw new Error(`API request failed with status ${response.status}`);
        }
        const data = await response.json();

        // Also fetch motion alerts
        const alertsResponse = await fetch(`${API_BASE_URL}/motion_alerts`);
        const alertsData = await alertsResponse.json();
        
        return { houses: data, motion_alerts: alertsData.activeAlerts || [] };
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
 * @param {object} data The combined data object from the API.
 */
function renderDashboard(data) {
    if (!data) return;
    renderGlobalAlert(data);

    houseGrid.innerHTML = ''; // Clear the grid before rendering new data

    if (Object.keys(data.houses).length === 0) {
        houseGrid.innerHTML = `<p class="text-muted">No houses found or available.</p>`;
        return;
    }

    for (const houseId in data.houses) {
        const house = data.houses[houseId];
        const houseCard = createHouseCard(house, data.motion_alerts);
        houseGrid.appendChild(houseCard);
    }
}


/**
 * Renders a global "THIEF DETECTED!" alert with specific location details.
 * @param {object} data The full data object containing houses and motion_alerts.
 */
function renderGlobalAlert(data) {
    const alertContainer = document.getElementById('global-alert-container');
    const motionAlerts = data.motion_alerts;

    if (motionAlerts && motionAlerts.length > 0) {
        // Create a more descriptive string for each alert
        const alertDetails = motionAlerts.map(alertKey => {
            const [houseID, floorID, unitID] = alertKey.split('-');
            return `House ${houseID}, Floor ${floorID}, Unit ${unitID}`;
        }).join('; '); // Join multiple alerts with a semicolon for clarity

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
        alertContainer.innerHTML = ''; // Clear the alert if no motion is detected
    }
}

/**
 * Creates an HTML card element for a single house, now with more detail.
 * @param {object} house The house data object.
 * @param {string[]} motionAlerts A list of unit keys with active motion alerts.
 * @returns {HTMLElement} The fully constructed house card element.
 */
function createHouseCard(house, motionAlerts) {
    const isBreached = house.floors.some(floor => 
        floor.units.some(unit => motionAlerts.includes(`${house.houseID}-${floor.floorID}-${unit.unitID}`))
    );

    const card = document.createElement('div');
    card.className = 'col';
    
    // NEW: We will build the HTML by iterating through floors and units to group devices
    let cardBodyHtml = '';
    
    house.floors.forEach(floor => {
        floor.units.forEach(unit => {
            // NEW: Add a subheader for each unit
            cardBodyHtml += `<h6 class="mt-3 text-muted">Floor ${floor.floorID} / Unit ${unit.unitID}</h6>`;
            
            if (unit.devicesList && unit.devicesList.length > 0) {
                cardBodyHtml += '<ul class="list-group list-group-flush">';
                unit.devicesList.forEach(device => {
                    const icon = getDeviceIcon(device.deviceName, device.deviceStatus);
                    const statusClass = device.deviceStatus.toLowerCase().replace(' ', '-');
                    const badgeColor = getStatusBadgeColor(device.deviceStatus);
                    
                    // NEW: Check if this specific device is causing an alert
                    const isAlerting = motionAlerts.includes(`${house.houseID}-${floor.floorID}-${unit.unitID}`) && device.deviceName.includes('motion');
                    const alertClass = isAlerting ? 'list-group-item-danger' : '';

                    cardBodyHtml += `
                        <li class="list-group-item d-flex justify-content-between align-items-center ${alertClass}">
                            <div>
                                <i class="bi ${icon} me-2"></i>
                                <strong>${device.deviceName}</strong>
                                <small class="text-muted d-block">Last Update: ${new Date(device.lastUpdate).toLocaleTimeString()}</small>
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

    if (cardBodyHtml === '') {
        cardBodyHtml = '<div class="card-body"><p class="text-muted">No devices found for this house.</p></div>';
    }

    const thingspeakLink = getThingSpeakLink(house.houseID);

    card.innerHTML = `
        <div class="card h-100 shadow-sm">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0">
                    <i class="bi bi-house-door-fill me-2"></i>House ${house.houseID}
                </h5>
                <span class="badge rounded-pill ${isBreached ? 'bg-danger security-status breach' : 'bg-success security-status'}">
                    <i class="bi ${isBreached ? 'bi-exclamation-shield-fill' : 'bi-shield-check'} me-1"></i>
                    ${isBreached ? 'BREACH' : 'SECURE'}
                </span>
            </div>
            <div class="card-body">
                ${cardBodyHtml}
            </div>
            <div class="card-footer bg-transparent border-top-0">
                <a href="${thingspeakLink}" class="btn btn-outline-primary btn-sm w-100" target="_blank">
                    <i class="bi bi-graph-up-arrow me-2"></i>View ThingSpeak Chart
                </a>
            </div>
        </div>`;
    return card;
}

// Helper functions for styling (no changes here)
function getDeviceIcon(deviceName, deviceStatus) {
    if (deviceName.includes('light_sensor')) return 'bi-brightness-high-fill';
    if (deviceName.includes('light_switch')) return 'bi-lightbulb-fill';
    if (deviceName.includes('motion')) return deviceStatus === 'Detected' ? 'bi-person-walking' : 'bi-shield-shaded';
    return 'bi-gear-fill';
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
    const channelMap = { '1': '2884625', '2': '2884626' }; // Make sure these are your correct channel IDs
    const channelId = channelMap[houseId];
    return channelId ? `https://thingspeak.com/channels/${channelId}` : '#';
}

// --- Theme Toggler --- (no changes here)
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


// --- Main Application Logic --- (no changes here)
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