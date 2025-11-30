// Global variables
let map;
let markers = [];
let allFirms = [];
let filteredFirms = [];
let selectedRegion = 'all';
let selectedDistrict = 'all';

// Coordinate offset to prevent overlapping markers
const MARKER_OFFSET = 0.01;

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

// Approximate coordinates for Korean locations (simplified geocoding)
const locationCoordinates = {
    // Seoul districts
    '서울특별시 강남구': { lat: 37.5172, lng: 127.0473 },
    '서울특별시 강동구': { lat: 37.5301, lng: 127.1238 },
    '서울특별시 강북구': { lat: 37.6396, lng: 127.0257 },
    '서울특별시 강서구': { lat: 37.5509, lng: 126.8495 },
    '서울특별시 관악구': { lat: 37.4784, lng: 126.9516 },
    '서울특별시 광진구': { lat: 37.5385, lng: 127.0823 },
    '서울특별시 구로구': { lat: 37.4954, lng: 126.8874 },
    '서울특별시 금천구': { lat: 37.4519, lng: 126.9020 },
    '서울특별시 노원구': { lat: 37.6542, lng: 127.0568 },
    '서울특별시 도봉구': { lat: 37.6688, lng: 127.0471 },
    '서울특별시 동대문구': { lat: 37.5744, lng: 127.0396 },
    '서울특별시 동작구': { lat: 37.5124, lng: 126.9393 },
    '서울특별시 마포구': { lat: 37.5663, lng: 126.9014 },
    '서울특별시 서대문구': { lat: 37.5791, lng: 126.9368 },
    '서울특별시 서초구': { lat: 37.4837, lng: 127.0324 },
    '서울특별시 성동구': { lat: 37.5633, lng: 127.0371 },
    '서울특별시 성북구': { lat: 37.5894, lng: 127.0167 },
    '서울특별시 송파구': { lat: 37.5145, lng: 127.1050 },
    '서울특별시 양천구': { lat: 37.5170, lng: 126.8664 },
    '서울특별시 영등포구': { lat: 37.5264, lng: 126.8962 },
    '서울특별시 용산구': { lat: 37.5324, lng: 126.9900 },
    '서울특별시 은평구': { lat: 37.6027, lng: 126.9291 },
    '서울특별시 종로구': { lat: 37.5735, lng: 126.9790 },
    '서울특별시 중구': { lat: 37.5641, lng: 126.9979 },
    '서울특별시 중랑구': { lat: 37.6063, lng: 127.0928 },
    // Busan districts
    '부산광역시 강서구': { lat: 35.2122, lng: 128.9803 },
    '부산광역시 금정구': { lat: 35.2428, lng: 129.0922 },
    '부산광역시 기장군': { lat: 35.2446, lng: 129.2222 },
    '부산광역시 남구': { lat: 35.1366, lng: 129.0845 },
    '부산광역시 동구': { lat: 35.1295, lng: 129.0458 },
    '부산광역시 동래구': { lat: 35.1972, lng: 129.0837 },
    '부산광역시 부산진구': { lat: 35.1631, lng: 129.0530 },
    '부산광역시 북구': { lat: 35.1972, lng: 128.9903 },
    '부산광역시 사상구': { lat: 35.1526, lng: 128.9915 },
    '부산광역시 사하구': { lat: 35.1046, lng: 128.9747 },
    '부산광역시 서구': { lat: 35.0976, lng: 129.0244 },
    '부산광역시 수영구': { lat: 35.1454, lng: 129.1131 },
    '부산광역시 연제구': { lat: 35.1760, lng: 129.0799 },
    '부산광역시 영도구': { lat: 35.0912, lng: 129.0680 },
    '부산광역시 중구': { lat: 35.1062, lng: 129.0321 },
    '부산광역시 해운대구': { lat: 35.1629, lng: 129.1635 },
    // Daejeon districts
    '대전광역시 대덕구': { lat: 36.3469, lng: 127.4156 },
    '대전광역시 동구': { lat: 36.3121, lng: 127.4549 },
    '대전광역시 서구': { lat: 36.3556, lng: 127.3835 },
    '대전광역시 유성구': { lat: 36.3623, lng: 127.3562 },
    '대전광역시 중구': { lat: 36.3256, lng: 127.4213 },
    // Daegu districts
    '대구광역시 군위군': { lat: 36.2427, lng: 128.5728 },
    '대구광역시 남구': { lat: 35.8461, lng: 128.5975 },
    '대구광역시 달서구': { lat: 35.8297, lng: 128.5332 },
    '대구광역시 달성군': { lat: 35.7746, lng: 128.4312 },
    '대구광역시 동구': { lat: 35.8858, lng: 128.6356 },
    '대구광역시 북구': { lat: 35.8856, lng: 128.5828 },
    '대구광역시 서구': { lat: 35.8722, lng: 128.5592 },
    '대구광역시 수성구': { lat: 35.8586, lng: 128.6308 },
    '대구광역시 중구': { lat: 35.8692, lng: 128.6062 },
    // Incheon districts
    '인천광역시 강화군': { lat: 37.7467, lng: 126.4878 },
    '인천광역시 계양구': { lat: 37.5370, lng: 126.7376 },
    '인천광역시 남동구': { lat: 37.4488, lng: 126.7312 },
    '인천광역시 동구': { lat: 37.4737, lng: 126.6432 },
    '인천광역시 미추홀구': { lat: 37.4637, lng: 126.6506 },
    '인천광역시 부평구': { lat: 37.5076, lng: 126.7219 },
    '인천광역시 서구': { lat: 37.5455, lng: 126.6760 },
    '인천광역시 연수구': { lat: 37.4100, lng: 126.6784 },
    '인천광역시 옹진군': { lat: 37.4467, lng: 126.6367 },
    '인천광역시 중구': { lat: 37.4736, lng: 126.6213 },
    // Gwangju districts
    '광주광역시 광산구': { lat: 35.1395, lng: 126.7936 },
    '광주광역시 남구': { lat: 35.1333, lng: 126.9025 },
    '광주광역시 동구': { lat: 35.1461, lng: 126.9231 },
    '광주광역시 북구': { lat: 35.1744, lng: 126.9122 },
    '광주광역시 서구': { lat: 35.1523, lng: 126.8895 },
    // Ulsan districts
    '울산광역시 남구': { lat: 35.5443, lng: 129.3304 },
    '울산광역시 동구': { lat: 35.5050, lng: 129.4165 },
    '울산광역시 북구': { lat: 35.5837, lng: 129.3612 },
    '울산광역시 울주군': { lat: 35.5222, lng: 129.0999 },
    '울산광역시 중구': { lat: 35.5683, lng: 129.3323 },
    // Gyeonggi cities (main ones)
    '경기도 수원시': { lat: 37.2636, lng: 127.0286 },
    '경기도 성남시': { lat: 37.4449, lng: 127.1389 },
    '경기도 용인시': { lat: 37.2411, lng: 127.1775 },
    '경기도 고양시': { lat: 37.6584, lng: 126.8320 },
    '경기도 화성시': { lat: 37.1993, lng: 126.8312 },
    '경기도 안양시': { lat: 37.3943, lng: 126.9568 },
    '경기도 평택시': { lat: 36.9921, lng: 127.1127 },
    '경기도 시흥시': { lat: 37.3801, lng: 126.8029 },
    '경기도 파주시': { lat: 37.7599, lng: 126.7800 },
    '경기도 의정부시': { lat: 37.7381, lng: 127.0337 },
    '경기도 김포시': { lat: 37.6153, lng: 126.7156 },
    '경기도 광명시': { lat: 37.4786, lng: 126.8646 },
    '경기도 광주시': { lat: 37.4295, lng: 127.2551 },
    '경기도 군포시': { lat: 37.3617, lng: 126.9352 },
    '경기도 하남시': { lat: 37.5394, lng: 127.2145 },
    '경기도 오산시': { lat: 37.1498, lng: 127.0775 },
    '경기도 이천시': { lat: 37.2725, lng: 127.4350 },
    '경기도 안산시': { lat: 37.3219, lng: 126.8309 },
    '경기도 안성시': { lat: 37.0079, lng: 127.2797 },
    '경기도 의왕시': { lat: 37.3446, lng: 126.9687 },
    '경기도 양주시': { lat: 37.7852, lng: 127.0460 },
    '경기도 포천시': { lat: 37.8949, lng: 127.2003 },
    '경기도 여주시': { lat: 37.2983, lng: 127.6370 },
    '경기도 동두천시': { lat: 37.9034, lng: 127.0606 },
    '경기도 과천시': { lat: 37.4295, lng: 126.9874 },
    '경기도 구리시': { lat: 37.5943, lng: 127.1297 },
    '경기도 남양주시': { lat: 37.6360, lng: 127.2165 },
    '경기도 부천시': { lat: 37.5034, lng: 126.7660 },
    // Sejong
    '세종특별자치시': { lat: 36.4800, lng: 127.2890 },
    // Other regions
    '강원특별자치도 춘천시': { lat: 37.8813, lng: 127.7298 },
    '강원특별자치도 원주시': { lat: 37.3422, lng: 127.9201 },
    '강원특별자치도 강릉시': { lat: 37.7519, lng: 128.8761 },
    '충청북도 청주시': { lat: 36.6424, lng: 127.4890 },
    '충청북도 충주시': { lat: 36.9910, lng: 127.9259 },
    '충청북도 진천군': { lat: 36.8554, lng: 127.4356 },
    '충청북도 음성군': { lat: 36.9399, lng: 127.6909 },
    '충청남도 천안시': { lat: 36.8151, lng: 127.1139 },
    '충청남도 아산시': { lat: 36.7898, lng: 127.0018 },
    '충청남도 서산시': { lat: 36.7845, lng: 126.4503 },
    '충청남도 공주시': { lat: 36.4465, lng: 127.1191 },
    '충청남도 예산군': { lat: 36.6824, lng: 126.8489 },
    '전북특별자치도 전주시': { lat: 35.8242, lng: 127.1480 },
    '전북특별자치도 군산시': { lat: 35.9674, lng: 126.7366 },
    '전북특별자치도 익산시': { lat: 35.9484, lng: 126.9578 },
    '전북특별자치도 정읍시': { lat: 35.5699, lng: 126.8558 },
    '전라남도 순천시': { lat: 34.9506, lng: 127.4871 },
    '전라남도 나주시': { lat: 35.0156, lng: 126.7108 },
    '전라남도 강진군': { lat: 34.6420, lng: 126.7670 },
    '전라남도 장흥군': { lat: 34.6816, lng: 126.9069 },
    '경상북도 포항시': { lat: 36.0190, lng: 129.3435 },
    '경상북도 경산시': { lat: 35.8251, lng: 128.7414 },
    '경상북도 구미시': { lat: 36.1195, lng: 128.3446 },
    '경상북도 안동시': { lat: 36.5684, lng: 128.7296 },
    '경상남도 창원시': { lat: 35.2286, lng: 128.6811 },
    '경상남도 진주시': { lat: 35.1804, lng: 128.1076 },
    '경상남도 김해시': { lat: 35.2343, lng: 128.8812 },
    '경상남도 양산시': { lat: 35.3350, lng: 129.0373 },
    '경상남도 창녕군': { lat: 35.5442, lng: 128.4916 },
    '제주특별자치도 제주시': { lat: 33.4996, lng: 126.5312 },
    '제주특별자치도 서귀포시': { lat: 33.2541, lng: 126.5600 }
};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initMap();
    loadCSVData();
    setupEventListeners();
    populateDistrictFilter();
});

// Initialize the map
function initMap() {
    // Check if Leaflet is available
    if (typeof L !== 'undefined' && L !== null) {
        map = L.map('map').setView([36.5, 127.5], 7);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 18
        }).addTo(map);
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

// Simple CSV parser (fallback for when PapaParse is not available)
function parseCSV(csvText) {
    const lines = csvText.split('\n');
    const headers = lines[0].split(',');
    const result = [];
    
    for (let i = 1; i < lines.length; i++) {
        if (lines[i].trim() === '') continue;
        
        const values = [];
        let current = '';
        let inQuotes = false;
        
        for (let j = 0; j < lines[i].length; j++) {
            const char = lines[i][j];
            if (char === '"') {
                inQuotes = !inQuotes;
            } else if (char === ',' && !inQuotes) {
                values.push(current.trim());
                current = '';
            } else {
                current += char;
            }
        }
        values.push(current.trim());
        
        const obj = {};
        headers.forEach((header, index) => {
            obj[header.trim()] = values[index] || '';
        });
        result.push(obj);
    }
    
    return result;
}

// Load CSV data
function loadCSVData() {
    // Use the data serving route from Flask
    const dataUrl = '/data/2025_전문연구요원_인원배정.csv';
    
    // Try PapaParse first, fallback to fetch if not available
    if (typeof Papa !== 'undefined') {
        Papa.parse(dataUrl, {
            download: true,
            header: true,
            encoding: 'UTF-8',
            complete: function(results) {
                allFirms = results.data.filter(firm => firm['업체명'] && firm['소재지']);
                filteredFirms = [...allFirms];
                updateDisplay();
            },
            error: function(error) {
                console.error('Error loading CSV:', error);
                loadCSVFallback();
            }
        });
    } else {
        loadCSVFallback();
    }
}

// Fallback CSV loading using fetch
function loadCSVFallback() {
    const dataUrl = '/data/2025_전문연구요원_인원배정.csv';
    
    fetch(dataUrl)
        .then(response => response.text())
        .then(csvText => {
            const results = parseCSV(csvText);
            allFirms = results.filter(firm => firm['업체명'] && firm['소재지']);
            filteredFirms = [...allFirms];
            updateDisplay();
        })
        .catch(error => {
            console.error('Error loading CSV:', error);
            document.getElementById('firmList').innerHTML = 
                '<div class="loading">데이터 로딩 중 오류가 발생했습니다.</div>';
        });
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
            
            // Zoom to firm location
            if (map) {
                const coords = getCoordinates(firm['소재지']);
                if (coords) {
                    map.setView([coords.lat, coords.lng], 15);
                    
                    // Open popup for matching marker
                    markers.forEach(marker => {
                        if (marker.firmData === firm) {
                            marker.openPopup();
                        }
                    });
                }
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
    
    // Add new markers
    filteredFirms.forEach(firm => {
        const coords = getCoordinates(firm['소재지']);
        if (coords) {
            const marker = L.circleMarker([coords.lat, coords.lng], {
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

// Get coordinates for an address
function getCoordinates(address) {
    if (!address) return null;
    
    // Try to match with known locations
    for (const [key, coords] of Object.entries(locationCoordinates)) {
        if (address.includes(key.split(' ').slice(0, 2).join(' '))) {
            // Add small random offset to prevent markers from stacking
            return {
                lat: coords.lat + (Math.random() - 0.5) * MARKER_OFFSET,
                lng: coords.lng + (Math.random() - 0.5) * MARKER_OFFSET
            };
        }
    }
    
    // Try to extract city/district from address and use generic coordinates
    const parts = address.split(' ');
    if (parts.length >= 2) {
        const cityDistrict = parts[0] + ' ' + parts[1];
        if (locationCoordinates[cityDistrict]) {
            return {
                lat: locationCoordinates[cityDistrict].lat + (Math.random() - 0.5) * MARKER_OFFSET,
                lng: locationCoordinates[cityDistrict].lng + (Math.random() - 0.5) * MARKER_OFFSET
            };
        }
    }
    
    return null;
}
