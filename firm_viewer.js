// Global variables
let map;
let markers = [];
let allFirms = [];
let filteredFirms = [];
let selectedRegion = 'all';
let selectedDistrict = 'all';
let currentTileLayer = null;

// Seoul districts (구) list
const seoulDistricts = [
    '강남구', '강동구', '강북구', '강서구', '관악구', '광진구', '구로구', '금천구',
    '노원구', '도봉구', '동대문구', '동작구', '마포구', '서대문구', '서초구',
    '성동구', '성북구', '송파구', '양천구', '영등포구', '용산구', '은평구',
    '종로구', '중구', '중랑구'
];

// Region center coordinates for map zoom
const regionCenters = {
    'all': { lat: 36.5, lng: 127.5, zoom: 7 },
    '서울': { lat: 37.5665, lng: 126.9780, zoom: 11 },
    '부산': { lat: 35.1796, lng: 129.0756, zoom: 11 },
    '대전': { lat: 36.3504, lng: 127.3845, zoom: 11 },
    '대구': { lat: 35.8714, lng: 128.6014, zoom: 11 },
    '인천': { lat: 37.4563, lng: 126.7052, zoom: 11 },
    '광주': { lat: 35.1595, lng: 126.8526, zoom: 11 },
    '울산': { lat: 35.5384, lng: 129.3114, zoom: 11 },
    '경기': { lat: 37.4138, lng: 127.5183, zoom: 9 },
    '세종': { lat: 36.4800, lng: 127.2890, zoom: 12 }
};

// Map tile layers - using various layers for better subway/transit visibility
const tileLayers = {
    opnvkarte: {
        url: 'https://tileserver.memomaps.de/tilegen/{z}/{x}/{y}.png',
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, © <a href="https://memomaps.de/">ÖPNVKarte</a>',
        name: '🚇 대중교통 지도 (지하철역 강조)'
    },
    osm: {
        url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        name: '기본 지도'
    },
    osmHot: {
        url: 'https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, Tiles style by <a href="https://www.hotosm.org/">Humanitarian OSM Team</a>',
        name: 'OSM HOT (고대비 지도)'
    },
    cartoDB: {
        url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors © <a href="https://carto.com/attributions">CARTO</a>',
        name: 'CartoDB Voyager'
    },
    cartoDBDark: {
        url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors © <a href="https://carto.com/attributions">CARTO</a>',
        name: 'CartoDB 다크 모드'
    },
    openRailway: {
        url: 'https://{s}.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png',
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, Style: <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA 2.0</a> <a href="http://www.openrailwaymap.org/">OpenRailwayMap</a>',
        name: '철도 노선 오버레이'
    }
};

// District centers for Seoul
const seoulDistrictCenters = {
    '강남구': { lat: 37.5172, lng: 127.0473, zoom: 13 },
    '강동구': { lat: 37.5301, lng: 127.1238, zoom: 13 },
    '강북구': { lat: 37.6396, lng: 127.0257, zoom: 13 },
    '강서구': { lat: 37.5509, lng: 126.8495, zoom: 13 },
    '관악구': { lat: 37.4784, lng: 126.9516, zoom: 13 },
    '광진구': { lat: 37.5385, lng: 127.0823, zoom: 13 },
    '구로구': { lat: 37.4954, lng: 126.8874, zoom: 13 },
    '금천구': { lat: 37.4519, lng: 126.9020, zoom: 13 },
    '노원구': { lat: 37.6542, lng: 127.0568, zoom: 13 },
    '도봉구': { lat: 37.6688, lng: 127.0471, zoom: 13 },
    '동대문구': { lat: 37.5744, lng: 127.0396, zoom: 13 },
    '동작구': { lat: 37.5124, lng: 126.9393, zoom: 13 },
    '마포구': { lat: 37.5663, lng: 126.9014, zoom: 13 },
    '서대문구': { lat: 37.5791, lng: 126.9368, zoom: 13 },
    '서초구': { lat: 37.4837, lng: 127.0324, zoom: 13 },
    '성동구': { lat: 37.5633, lng: 127.0371, zoom: 13 },
    '성북구': { lat: 37.5894, lng: 127.0167, zoom: 13 },
    '송파구': { lat: 37.5145, lng: 127.1050, zoom: 13 },
    '양천구': { lat: 37.5170, lng: 126.8664, zoom: 13 },
    '영등포구': { lat: 37.5264, lng: 126.8962, zoom: 13 },
    '용산구': { lat: 37.5324, lng: 126.9900, zoom: 13 },
    '은평구': { lat: 37.6027, lng: 126.9291, zoom: 13 },
    '종로구': { lat: 37.5735, lng: 126.9790, zoom: 13 },
    '중구': { lat: 37.5641, lng: 126.9979, zoom: 13 },
    '중랑구': { lat: 37.6063, lng: 127.0928, zoom: 13 }
};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initMap();
    loadFirmsData();
    setupEventListeners();
    populateDistrictFilter();
});

// Initialize the map with ÖPNVKarte transit layer (prominently shows subway stations)
function initMap() {
    // Check if Leaflet is available
    if (typeof L !== 'undefined' && L !== null) {
        map = L.map('map').setView([36.5, 127.5], 7);
        
        // ÖPNVKarte transit layer - prominently shows subway stations
        const transitLayer = L.tileLayer(tileLayers.opnvkarte.url, {
            attribution: tileLayers.opnvkarte.attribution,
            maxZoom: 18
        });
        
        // Standard OSM layer
        const osmLayer = L.tileLayer(tileLayers.osm.url, {
            attribution: tileLayers.osm.attribution,
            maxZoom: 19
        });
        
        const osmHotLayer = L.tileLayer(tileLayers.osmHot.url, {
            attribution: tileLayers.osmHot.attribution,
            maxZoom: 19
        });
        
        const cartoLayer = L.tileLayer(tileLayers.cartoDB.url, {
            attribution: tileLayers.cartoDB.attribution,
            maxZoom: 19,
            subdomains: 'abcd'
        });
        
        const cartoDarkLayer = L.tileLayer(tileLayers.cartoDBDark.url, {
            attribution: tileLayers.cartoDBDark.attribution,
            maxZoom: 19,
            subdomains: 'abcd'
        });
        
        // OpenRailwayMap overlay layer for subway/railway visibility
        const railwayOverlay = L.tileLayer(tileLayers.openRailway.url, {
            attribution: tileLayers.openRailway.attribution,
            maxZoom: 19,
            opacity: 0.8
        });
        
        // Default to ÖPNVKarte transit map (prominently shows subway stations)
        transitLayer.addTo(map);
        currentTileLayer = transitLayer;
        
        // Add layer control with map options
        const baseLayers = {
            "🚇 대중교통 지도 (지하철역 강조)": transitLayer,
            "🗺️ 기본 지도 (OSM)": osmLayer,
            "🌡️ OSM HOT (고대비 지도)": osmHotLayer,
            "🏙️ CartoDB Voyager": cartoLayer,
            "🌙 CartoDB 다크 모드": cartoDarkLayer
        };
        
        const overlays = {
            "🚃 철도/지하철 노선 오버레이": railwayOverlay
        };
        
        L.control.layers(baseLayers, overlays).addTo(map);
        
    } else {
        // Fallback when Leaflet is not available
        document.getElementById('map').innerHTML = `
            <div style="display: flex; justify-content: center; align-items: center; height: 100%; flex-direction: column; color: #7f8c8d; text-align: center; padding: 20px;">
                <p>지도를 로드할 수 없습니다.</p>
                <p style="font-size: 12px; margin-top: 10px;">CDN 접근이 필요합니다.</p>
            </div>
        `;
    }
}

// Load firms data from pre-geocoded firms_data.js
function loadFirmsData() {
    // Check if firmsData is loaded from firms_data.js
    if (typeof firmsData !== 'undefined' && firmsData.length > 0) {
        // Transform firmsData to match the expected format
        allFirms = firmsData.map(firm => ({
            '업체명': firm.name,
            '소재지': firm.address,
            '업종구분': firm.type,
            '25년 배정인원': firm.allocation,
            '관할청': firm.jurisdiction,
            'lat': firm.lat,
            'lng': firm.lng
        }));
        filteredFirms = [...allFirms];
        updateDisplay();
    } else {
        console.error('Firms data not loaded! Make sure firms_data.js is included.');
        document.getElementById('firmList').innerHTML = 
            '<div class="loading">데이터 로딩 중 오류가 발생했습니다.</div>';
    }
}

// Setup event listeners
function setupEventListeners() {
    // Region tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', function() {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            selectedRegion = this.dataset.region;
            selectedDistrict = 'all';
            
            // Show/hide district filter for Seoul
            const districtFilter = document.getElementById('districtFilter');
            if (selectedRegion === '서울') {
                districtFilter.style.display = 'flex';
                document.getElementById('seoulDistrict').value = 'all';
            } else {
                districtFilter.style.display = 'none';
            }
            
            filterFirms();
            updateMapView();
        });
    });

    // District filter
    document.getElementById('seoulDistrict').addEventListener('change', function() {
        selectedDistrict = this.value;
        filterFirms();
        updateMapViewForDistrict();
    });

    // Search
    document.getElementById('searchInput').addEventListener('input', function() {
        filterFirms();
    });
}

// Populate district filter
function populateDistrictFilter() {
    const select = document.getElementById('seoulDistrict');
    seoulDistricts.forEach(district => {
        const option = document.createElement('option');
        option.value = district;
        option.textContent = district;
        select.appendChild(option);
    });
}

// Filter firms based on region, district, and search
function filterFirms() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    
    filteredFirms = allFirms.filter(firm => {
        const address = firm['소재지'] || '';
        const name = firm['업체명'] || '';
        
        // Region filter
        let regionMatch = true;
        if (selectedRegion !== 'all') {
            if (selectedRegion === '서울') {
                regionMatch = address.includes('서울');
            } else if (selectedRegion === '부산') {
                regionMatch = address.includes('부산');
            } else if (selectedRegion === '대전') {
                regionMatch = address.includes('대전');
            } else if (selectedRegion === '대구') {
                regionMatch = address.includes('대구');
            } else if (selectedRegion === '인천') {
                regionMatch = address.includes('인천');
            } else if (selectedRegion === '광주') {
                regionMatch = address.includes('광주');
            } else if (selectedRegion === '울산') {
                regionMatch = address.includes('울산');
            } else if (selectedRegion === '경기') {
                regionMatch = address.includes('경기');
            } else if (selectedRegion === '세종') {
                regionMatch = address.includes('세종');
            }
        }
        
        // District filter for Seoul
        let districtMatch = true;
        if (selectedRegion === '서울' && selectedDistrict !== 'all') {
            districtMatch = address.includes(selectedDistrict);
        }
        
        // Search filter
        let searchMatch = true;
        if (searchTerm) {
            searchMatch = name.toLowerCase().includes(searchTerm) || 
                          address.toLowerCase().includes(searchTerm);
        }
        
        return regionMatch && districtMatch && searchMatch;
    });
    
    updateDisplay();
}

// Update map view for selected region
function updateMapView() {
    if (!map) return;
    const center = regionCenters[selectedRegion] || regionCenters['all'];
    map.setView([center.lat, center.lng], center.zoom);
}

// Update map view for selected district
function updateMapViewForDistrict() {
    if (!map) return;
    if (selectedDistrict !== 'all' && seoulDistrictCenters[selectedDistrict]) {
        const center = seoulDistrictCenters[selectedDistrict];
        map.setView([center.lat, center.lng], center.zoom);
    } else if (selectedRegion === '서울') {
        updateMapView();
    }
}

// Update display (both map and list)
function updateDisplay() {
    updateFirmList();
    updateMarkers();
    document.getElementById('firmCount').textContent = filteredFirms.length.toLocaleString();
}

// Update firm list
function updateFirmList() {
    const listContainer = document.getElementById('firmList');
    listContainer.innerHTML = '';
    
    if (filteredFirms.length === 0) {
        listContainer.innerHTML = '<div class="loading">검색 결과가 없습니다.</div>';
        return;
    }
    
    filteredFirms.forEach((firm, index) => {
        const item = document.createElement('div');
        item.className = 'firm-item';
        item.innerHTML = `
            <div class="name">${firm['업체명'] || '-'}</div>
            <div class="address">${firm['소재지'] || '-'}</div>
            <div class="info">
                <span class="badge type">${firm['업종구분'] || '-'}</span>
                <span class="badge allocation">${firm['25년 배정인원'] || '-'}</span>
            </div>
        `;
        
        item.addEventListener('click', () => {
            // Highlight selected item
            document.querySelectorAll('.firm-item').forEach(el => el.classList.remove('selected'));
            item.classList.add('selected');
            
            // Zoom to firm location using pre-geocoded coordinates
            if (map && firm.lat && firm.lng) {
                map.setView([firm.lat, firm.lng], 15);
                
                // Open popup for matching marker
                markers.forEach(marker => {
                    if (marker.firmData === firm) {
                        marker.openPopup();
                    }
                });
            }
        });
        
        listContainer.appendChild(item);
    });
}

// Update map markers
function updateMarkers() {
    if (!map || typeof L === 'undefined') return;
    
    // Clear existing markers
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];
    
    // Add new markers using pre-geocoded coordinates from firms_data.js
    filteredFirms.forEach(firm => {
        // Use pre-geocoded coordinates from firm data
        if (firm.lat && firm.lng) {
            const marker = L.circleMarker([firm.lat, firm.lng], {
                radius: 8,
                fillColor: '#3498db',
                color: '#fff',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.8
            });
            
            marker.firmData = firm;
            
            const popupContent = `
                <div class="popup-content">
                    <h3>${firm['업체명'] || '-'}</h3>
                    <p><strong>주소:</strong> ${firm['소재지'] || '-'}</p>
                    <p><strong>관할청:</strong> ${firm['관할청'] || '-'}</p>
                    <span class="badge">${firm['업종구분'] || '-'}</span>
                    <span class="badge" style="background: #e8f5e9; color: #388e3c;">${firm['25년 배정인원'] || '-'}</span>
                </div>
            `;
            
            marker.bindPopup(popupContent);
            marker.addTo(map);
            markers.push(marker);
        }
    });
}
