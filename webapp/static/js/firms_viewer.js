// Global variables
let map = null;
let clusterer = null;
let allFirms = [];
let currentRegion = 'all';
let currentGu = 'all';
let searchQuery = '';
let kakaoMapAvailable = false;
let activeOverlay = null;
let searchTimeout = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    kakaoMapAvailable = window.ENABLE_KAKAO_MAP && typeof kakao !== 'undefined';
    
    // Always load the firm list and setup events immediately, independent of the map
    loadFirmsData();
    setupEventListeners();
    
    if (kakaoMapAvailable) {
        let mapLoaded = false;
        
        kakao.maps.load(function() {
            mapLoaded = true;
            initMap();
            updateDisplay(); // update markers now that map is ready
        });
        
        // Timeout fallback: if Kakao's actual map script fails to load (e.g. Origin Not Allowed by Kakao servers)
        setTimeout(function() {
            if (!mapLoaded) {
                kakaoMapAvailable = false;
                initMap(); // show error message
            }
        }, 3000);
    } else {
        initMap(); // immediately show error message
    }
});

function initMap() {
    const mapContainer = document.getElementById('map');
    
    if (!kakaoMapAvailable) {
        mapContainer.innerHTML = '<div class="no-map-message">지도를 로드할 수 없습니다.<br>도메인이 카카오 디벨로퍼스에 등록되지 않았거나 네트워크 오류입니다.<br>왼쪽 목록에서 업체를 확인해주세요.</div>';
        return;
    }
    
    const options = {
        center: new kakao.maps.LatLng(36.5, 127.5),
        level: 13
    };
    
    map = new kakao.maps.Map(mapContainer, options);
    
    // Zoom control
    const zoomControl = new kakao.maps.ZoomControl();
    map.addControl(zoomControl, kakao.maps.ControlPosition.RIGHT);
    
    // Clusterer
    clusterer = new kakao.maps.MarkerClusterer({
        map: map,
        averageCenter: true, 
        minLevel: 10
    });
    
    // Single shared overlay for better performance
    activeOverlay = new kakao.maps.CustomOverlay({
        yAnchor: 1.5,
        zIndex: 3
    });
    
    kakao.maps.event.addListener(map, 'click', function() {
        if (activeOverlay) {
            activeOverlay.setMap(null);
        }
    });
}

function loadFirmsData() {
    if (typeof firmsData !== 'undefined') {
        allFirms = firmsData;
        document.getElementById('total-count').textContent = allFirms.length;
        updateFirmsList(getFilteredFirms()); // Initialize list only initially
    } else {
        console.error('Firms data not loaded!');
    }
}

function setupEventListeners() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentRegion = this.dataset.region;
            currentGu = 'all';
            document.getElementById('gu-select').value = 'all';
            
            const seoulFilter = document.getElementById('seoul-filter');
            if (currentRegion === '서울') {
                seoulFilter.classList.remove('hidden');
            } else {
                seoulFilter.classList.add('hidden');
            }
            
            updateDisplay();
        });
    });
    
    document.getElementById('gu-select').addEventListener('change', function() {
        currentGu = this.value;
        updateDisplay();
    });
    
    document.getElementById('search-input').addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            searchQuery = this.value.toLowerCase();
            updateDisplay();
        }, 300);
    });
}

function getFilteredFirms() {
    return allFirms.filter(firm => {
        if (currentRegion !== 'all' && firm.jurisdiction !== currentRegion) {
            return false;
        }
        if (currentRegion === '서울' && currentGu !== 'all') {
            if (!firm.address.includes(currentGu)) {
                return false;
            }
        }
        if (searchQuery && !firm.name.toLowerCase().includes(searchQuery)) {
            return false;
        }
        return true;
    });
}

function updateDisplay() {
    const filteredFirms = getFilteredFirms();
    document.getElementById('filtered-count').textContent = filteredFirms.length;
    
    // Update Map if available
    if (kakaoMapAvailable && map && clusterer) {
        clusterer.clear();
        
        if (activeOverlay) {
            activeOverlay.setMap(null);
        }
        
        const bounds = new kakao.maps.LatLngBounds();
        let hasValidMarkers = false;
        
        const markers = filteredFirms.map(firm => {
            if (firm.lat && firm.lng) {
                const position = new kakao.maps.LatLng(firm.lat, firm.lng);
                const marker = new kakao.maps.Marker({
                    position: position
                });
                
                bounds.extend(position);
                hasValidMarkers = true;
                
                kakao.maps.event.addListener(marker, 'click', function() {
                    const content = `
                        <div style="padding:10px;background:#fff;border:1px solid #ccc;border-radius:5px;box-shadow:0 2px 4px rgba(0,0,0,0.2);">
                            <div class="popup-title" style="font-weight:bold;margin-bottom:4px;">${firm.name}</div>
                            <div class="popup-type" style="color:#666;font-size:12px;margin-bottom:4px;">${firm.type}</div>
                            <div class="popup-address" style="font-size:12px;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:250px;">${firm.address}</div>
                            <div class="popup-allocation" style="color:#e74c3c;font-size:12px;font-weight:bold;">배정인원: ${firm.allocation}</div>
                        </div>
                    `;
                    activeOverlay.setContent(content);
                    activeOverlay.setPosition(marker.getPosition());
                    activeOverlay.setMap(map);
                });
                
                return marker;
            }
            return null;
        }).filter(m => m !== null);
        
        clusterer.addMarkers(markers);
        
        // Auto-configure the map view to contain all markers
        if (hasValidMarkers) {
            map.setBounds(bounds);
        } else {
            // Default center if no markers
            map.setCenter(new kakao.maps.LatLng(36.5, 127.5));
            map.setLevel(13);
        }
    }
    
    // Always update list
    updateFirmsList(filteredFirms);
}

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
        
        card.addEventListener('click', () => {
            if (kakaoMapAvailable && map && firm.lat && firm.lng) {
                map.setLevel(4);
                map.setCenter(new kakao.maps.LatLng(firm.lat, firm.lng));
            }
        });
        
        listContainer.appendChild(card);
    });
}
