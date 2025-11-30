// Region coordinates for zooming
const regionCoords = {
    'all': { lat: 36.5, lng: 127.5, zoom: 7 },
    '서울': { lat: 37.5665, lng: 126.9780, zoom: 11 },
    '경인': { lat: 37.4, lng: 127.0, zoom: 10 },
    '인천': { lat: 37.4563, lng: 126.7052, zoom: 11 },
    '대전.충남': { lat: 36.35, lng: 127.0, zoom: 9 },
    '부산.울산': { lat: 35.4, lng: 129.1, zoom: 10 },
    '대구.경북': { lat: 35.9, lng: 128.6, zoom: 9 },
    '광주.전남': { lat: 35.0, lng: 126.9, zoom: 9 },
    '충북': { lat: 36.8, lng: 127.7, zoom: 9 },
    '경남': { lat: 35.3, lng: 128.3, zoom: 9 },
    '강원': { lat: 37.7, lng: 128.3, zoom: 9 },
    '전북': { lat: 35.8, lng: 127.1, zoom: 9 },
    '제주': { lat: 33.4, lng: 126.5, zoom: 10 },
    '경기북부': { lat: 37.8, lng: 127.0, zoom: 10 },
    '강원영동': { lat: 37.8, lng: 128.9, zoom: 10 }
};

// Seoul Gu coordinates for zooming
const seoulGuCoords = {
    'all': { lat: 37.5665, lng: 126.9780, zoom: 11 },
    '강남구': { lat: 37.5172, lng: 127.0473, zoom: 13 },
    '강동구': { lat: 37.5301, lng: 127.1237, zoom: 13 },
    '강서구': { lat: 37.5509, lng: 126.8495, zoom: 13 },
    '관악구': { lat: 37.4784, lng: 126.9516, zoom: 13 },
    '광진구': { lat: 37.5384, lng: 127.0823, zoom: 13 },
    '구로구': { lat: 37.4954, lng: 126.8874, zoom: 13 },
    '금천구': { lat: 37.4600, lng: 126.9000, zoom: 13 },
    '노원구': { lat: 37.6542, lng: 127.0568, zoom: 13 },
    '도봉구': { lat: 37.6688, lng: 127.0471, zoom: 13 },
    '동대문구': { lat: 37.5744, lng: 127.0395, zoom: 13 },
    '동작구': { lat: 37.5124, lng: 126.9393, zoom: 13 },
    '마포구': { lat: 37.5663, lng: 126.9014, zoom: 13 },
    '서대문구': { lat: 37.5791, lng: 126.9368, zoom: 13 },
    '서초구': { lat: 37.4837, lng: 127.0324, zoom: 13 },
    '성동구': { lat: 37.5633, lng: 127.0371, zoom: 13 },
    '성북구': { lat: 37.5894, lng: 127.0167, zoom: 13 },
    '송파구': { lat: 37.5145, lng: 127.1059, zoom: 13 },
    '양천구': { lat: 37.5170, lng: 126.8665, zoom: 13 },
    '영등포구': { lat: 37.5263, lng: 126.8962, zoom: 13 },
    '용산구': { lat: 37.5324, lng: 126.9906, zoom: 13 },
    '은평구': { lat: 37.6176, lng: 126.9227, zoom: 13 },
    '종로구': { lat: 37.5730, lng: 126.9794, zoom: 13 },
    '중구': { lat: 37.5636, lng: 126.9976, zoom: 13 }
};

// Global variables
let map = null;
let markers = [];
let allFirms = [];
let currentRegion = 'all';
let currentGu = 'all';
let searchQuery = '';
let leafletAvailable = false;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    // Check if Leaflet is available
    leafletAvailable = typeof L !== 'undefined';
    
    initMap();
    loadFirmsData();
    setupEventListeners();
});

// Initialize Leaflet map or show fallback
function initMap() {
    const mapContainer = document.getElementById('map');
    
    if (!leafletAvailable) {
        // Show fallback message
        mapContainer.innerHTML = '<div class="no-map-message">지도를 로드할 수 없습니다.<br>지도 기능은 외부 서버 연결이 필요합니다.<br>아래 목록에서 업체를 확인해주세요.</div>';
        return;
    }
    
    map = L.map('map').setView([36.5, 127.5], 7);
    
    // Base layer - CartoDB Voyager for cleaner look
    const cartoLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
    });
    
    const osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    });
    
    // OpenRailwayMap overlay for subway/railway visibility
    const railwayOverlay = L.tileLayer('https://{s}.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png', {
        attribution: 'Style: <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA 2.0</a> <a href="http://www.openrailwaymap.org/">OpenRailwayMap</a>',
        maxZoom: 19,
        opacity: 0.8
    });
    
    // Add base layer and railway overlay
    cartoLayer.addTo(map);
    railwayOverlay.addTo(map);
    
    // Layer control
    const baseLayers = {
        "CartoDB Voyager (지하철 표시)": cartoLayer,
        "기본 지도": osmLayer
    };
    
    const overlays = {
        "지하철/철도 노선": railwayOverlay
    };
    
    L.control.layers(baseLayers, overlays).addTo(map);
}

// Load firms data
function loadFirmsData() {
    // Check if firmsData is loaded from firms_data.js
    if (typeof firmsData !== 'undefined') {
        allFirms = firmsData;
        document.getElementById('total-count').textContent = allFirms.length;
        updateDisplay();
    } else {
        console.error('Firms data not loaded!');
    }
}

// Setup event listeners
function setupEventListeners() {
    // Tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentRegion = this.dataset.region;
            currentGu = 'all';
            document.getElementById('gu-select').value = 'all';
            
            // Show/hide Seoul filter
            const seoulFilter = document.getElementById('seoul-filter');
            if (currentRegion === '서울') {
                seoulFilter.classList.remove('hidden');
            } else {
                seoulFilter.classList.add('hidden');
            }
            
            updateDisplay();
        });
    });
    
    // Seoul Gu selector
    document.getElementById('gu-select').addEventListener('change', function() {
        currentGu = this.value;
        updateDisplay();
    });
    
    // Search input
    document.getElementById('search-input').addEventListener('input', function() {
        searchQuery = this.value.toLowerCase();
        updateDisplay();
    });
}

// Filter firms based on current criteria
function getFilteredFirms() {
    return allFirms.filter(firm => {
        // Region filter
        if (currentRegion !== 'all' && firm.jurisdiction !== currentRegion) {
            return false;
        }
        
        // Seoul Gu filter
        if (currentRegion === '서울' && currentGu !== 'all') {
            if (!firm.address.includes(currentGu)) {
                return false;
            }
        }
        
        // Search filter
        if (searchQuery && !firm.name.toLowerCase().includes(searchQuery)) {
            return false;
        }
        
        return true;
    });
}

// Update map and list display
function updateDisplay() {
    const filteredFirms = getFilteredFirms();
    
    // Update count
    document.getElementById('filtered-count').textContent = filteredFirms.length;
    
    // Only update map if Leaflet is available
    if (leafletAvailable && map) {
        // Clear existing markers
        markers.forEach(marker => map.removeLayer(marker));
        markers = [];
        
        // Add markers for filtered firms
        filteredFirms.forEach(firm => {
            if (firm.lat && firm.lng) {
                const marker = L.marker([firm.lat, firm.lng])
                    .bindPopup(`
                        <div class="popup-title">${firm.name}</div>
                        <div class="popup-type">${firm.type}</div>
                        <div class="popup-address">${firm.address}</div>
                        <div class="popup-allocation">배정인원: ${firm.allocation}</div>
                    `);
                marker.addTo(map);
                markers.push(marker);
            }
        });
        
        // Update map view
        if (currentRegion === '서울' && currentGu !== 'all') {
            const coords = seoulGuCoords[currentGu] || seoulGuCoords['all'];
            map.setView([coords.lat, coords.lng], coords.zoom);
        } else {
            const coords = regionCoords[currentRegion] || regionCoords['all'];
            map.setView([coords.lat, coords.lng], coords.zoom);
        }
    }
    
    // Update firms list
    updateFirmsList(filteredFirms);
}

// Update the firms list panel
function updateFirmsList(firms) {
    const listContainer = document.getElementById('firms-list');
    listContainer.innerHTML = '';
    
    firms.forEach(firm => {
        const card = document.createElement('div');
        card.className = 'firm-card';
        card.innerHTML = `
            <div class="firm-name">${firm.name}</div>
            <div class="firm-type">${firm.type}</div>
            <div class="firm-address">${firm.address}</div>
            <div class="firm-allocation">배정인원: ${firm.allocation}</div>
        `;
        
        // Click to zoom to location (only if map is available)
        card.addEventListener('click', () => {
            if (leafletAvailable && map && firm.lat && firm.lng) {
                map.setView([firm.lat, firm.lng], 15);
                // Find and open popup for this marker
                markers.forEach(marker => {
                    const latLng = marker.getLatLng();
                    if (Math.abs(latLng.lat - firm.lat) < 0.0001 && 
                        Math.abs(latLng.lng - firm.lng) < 0.0001) {
                        marker.openPopup();
                    }
                });
            }
        });
        
        listContainer.appendChild(card);
    });
}
