// The 인원배정 map: region chips, a firm list and, when the Kakao SDK loads, a
// clustered map. `firmsData` (and `firmsDataSource`) come from firms_data.js,
// which `uv run firm-geocode` writes from the active 인원배정 list.
//
// Every value shown comes from that list, so it is set with textContent,
// never innerHTML.

(function () {
    'use strict';

    /** Preferred order of 관할청 chips; any other region follows, by size. */
    const REGION_ORDER = [
        '서울', '경인', '경기북부', '인천', '대전.충남', '부산.울산', '대구.경북',
        '광주.전남', '충북', '경남', '강원', '강원영동', '전북', '제주',
    ];
    const KOREA_CENTER = [36.4, 127.8];
    const KAKAO_TIMEOUT_MS = 8000;
    const FOCUS_LEVEL = 5;

    const state = {
        firms: [],
        region: 'all',
        gu: 'all',
        query: '',
        selectedId: null,
    };

    let map = null;
    let clusterer = null;
    let popup = null;
    /** firm id -> Kakao marker, for the firms currently shown. */
    let markersById = new Map();

    // ------------------------------------------------------------ helpers

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined && text !== null) node.textContent = String(text);
        return node;
    }

    function regionLabel(region) {
        return region.replace(/\./g, '/');
    }

    function spotKey(firm) {
        return `${Number(firm.lat).toFixed(5)},${Number(firm.lng).toFixed(5)}`;
    }

    function hasCoords(firm) {
        return Number.isFinite(firm.lat) && Number.isFinite(firm.lng);
    }

    function allocationText(firm) {
        const value = String(firm.allocation ?? '').trim();
        if (!value) return '';
        return /^\d+$/.test(value) ? `배정 ${value}명` : value;
    }

    function seoulGu(address) {
        const parts = String(address || '').split(/\s+/);
        return parts[0] && parts[0].startsWith('서울') && parts[1] && parts[1].endsWith('구')
            ? parts[1]
            : null;
    }

    // ------------------------------------------------------------ filters

    function filteredFirms() {
        const query = state.query;
        return state.firms.filter((firm) => {
            if (state.region !== 'all' && firm.jurisdiction !== state.region) return false;
            if (state.region === '서울' && state.gu !== 'all' && seoulGu(firm.address) !== state.gu) {
                return false;
            }
            if (query) {
                const haystack = `${firm.name} ${firm.address}`.toLowerCase();
                if (!haystack.includes(query)) return false;
            }
            return true;
        });
    }

    function buildRegionChips() {
        const counts = new Map();
        state.firms.forEach((firm) => {
            const region = firm.jurisdiction || '기타';
            counts.set(region, (counts.get(region) || 0) + 1);
        });
        const regions = [...counts.keys()].sort((a, b) => {
            const ia = REGION_ORDER.indexOf(a);
            const ib = REGION_ORDER.indexOf(b);
            if (ia !== -1 || ib !== -1) return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
            return counts.get(b) - counts.get(a);
        });

        const container = document.getElementById('region-chips');
        container.replaceChildren();
        const addChip = (value, label, count) => {
            const chip = el('button', 'chip');
            chip.type = 'button';
            chip.dataset.region = value;
            chip.setAttribute('aria-pressed', String(state.region === value));
            chip.append(document.createTextNode(label), el('span', 'chip-count', count));
            chip.addEventListener('click', () => selectRegion(value));
            container.append(chip);
        };
        addChip('all', '전체', state.firms.length);
        regions.forEach((region) => addChip(region, regionLabel(region), counts.get(region)));
    }

    function buildGuOptions() {
        const select = document.getElementById('gu-select');
        const gus = [...new Set(state.firms.map((f) => seoulGu(f.address)).filter(Boolean))].sort(
            (a, b) => a.localeCompare(b, 'ko'),
        );
        gus.forEach((gu) => {
            const option = el('option', null, gu);
            option.value = gu;
            select.append(option);
        });
    }

    function selectRegion(region) {
        state.region = region;
        state.gu = 'all';
        document.getElementById('gu-select').value = 'all';
        document.getElementById('gu-filter').hidden = region !== '서울';
        document.querySelectorAll('#region-chips .chip').forEach((chip) => {
            chip.setAttribute('aria-pressed', String(chip.dataset.region === region));
        });
        update({ fit: true });
    }

    // --------------------------------------------------------------- list

    function renderList(firms) {
        const list = document.getElementById('firms-list');
        list.replaceChildren();
        if (!firms.length) {
            list.append(el('li', 'list-empty', '조건에 맞는 기관이 없습니다.'));
            return;
        }
        const fragment = document.createDocumentFragment();
        firms.forEach((firm) => {
            const item = el('li');
            const button = el('button', 'firm-item');
            button.type = 'button';
            button.dataset.id = firm.id;
            button.setAttribute('aria-current', String(firm.id === state.selectedId));

            const meta = el('span', 'firm-meta');
            if (firm.type) meta.append(el('span', 'firm-type', firm.type));
            meta.append(el('span', null, regionLabel(firm.jurisdiction || '')));
            const allocation = allocationText(firm);
            if (allocation) meta.append(el('span', 'firm-allocation', allocation));

            button.append(
                el('span', 'firm-name', firm.name),
                meta,
                el('span', 'firm-address', firm.address),
            );
            button.addEventListener('click', () => focusFirm(firm));
            item.append(button);
            fragment.append(item);
        });
        list.append(fragment);
    }

    function markCurrent() {
        document.querySelectorAll('#firms-list .firm-item').forEach((button) => {
            button.setAttribute('aria-current', String(button.dataset.id === state.selectedId));
        });
    }

    // ---------------------------------------------------------------- map

    function showMapMessage(title, detail) {
        const container = document.getElementById('map');
        container.replaceChildren();
        const box = el('div', 'no-map-message');
        box.append(el('strong', null, title), el('span', null, detail));
        container.append(box);
    }

    function initMap() {
        const container = document.getElementById('map');
        container.replaceChildren();
        map = new kakao.maps.Map(container, {
            center: new kakao.maps.LatLng(KOREA_CENTER[0], KOREA_CENTER[1]),
            level: 12,
        });
        map.addControl(new kakao.maps.ZoomControl(), kakao.maps.ControlPosition.RIGHT);

        const base = {
            borderRadius: '50%',
            color: '#fff',
            textAlign: 'center',
            fontWeight: '700',
            border: '2px solid rgba(255, 255, 255, 0.9)',
            boxShadow: '0 2px 6px rgba(15, 23, 42, 0.35)',
        };
        clusterer = new kakao.maps.MarkerClusterer({
            map,
            averageCenter: true,
            minLevel: 7,
            calculator: [10, 50, 150],
            styles: [
                { ...base, width: '34px', height: '34px', lineHeight: '30px', fontSize: '12px', background: 'rgba(59, 130, 246, 0.92)' },
                { ...base, width: '42px', height: '42px', lineHeight: '38px', fontSize: '13px', background: 'rgba(79, 70, 229, 0.92)' },
                { ...base, width: '50px', height: '50px', lineHeight: '46px', fontSize: '14px', background: 'rgba(124, 58, 237, 0.92)' },
                { ...base, width: '58px', height: '58px', lineHeight: '54px', fontSize: '15px', background: 'rgba(147, 51, 234, 0.95)' },
            ],
        });
        popup = new kakao.maps.CustomOverlay({ yAnchor: 1, zIndex: 5, clickable: true });
        kakao.maps.event.addListener(map, 'click', closePopup);

        // The container may have been laid out while hidden or resized since.
        window.addEventListener('resize', () => map && map.relayout());
    }

    function renderMarkers(firms, fit) {
        if (!map) return;
        closePopup();
        clusterer.clear();
        markersById = new Map();

        const bounds = new kakao.maps.LatLngBounds();
        const markers = [];
        firms.forEach((firm) => {
            if (!hasCoords(firm)) return;
            const position = new kakao.maps.LatLng(firm.lat, firm.lng);
            const marker = new kakao.maps.Marker({ position, title: firm.name });
            kakao.maps.event.addListener(marker, 'click', () => {
                selectFirm(firm.id);
                openPopup(firm);
            });
            markersById.set(firm.id, marker);
            markers.push(marker);
            bounds.extend(position);
        });
        clusterer.addMarkers(markers);

        if (!fit) return;
        if (markers.length) {
            map.setBounds(bounds, 24, 24, 24, 24);
        } else {
            map.setLevel(12);
            map.setCenter(new kakao.maps.LatLng(KOREA_CENTER[0], KOREA_CENTER[1]));
        }
    }

    function closePopup() {
        if (popup) popup.setMap(null);
    }

    /** A card for every shown firm at `firm`'s spot, with `firm` first. */
    function openPopup(firm) {
        if (!map || !hasCoords(firm)) return;
        const key = spotKey(firm);
        const here = filteredFirms().filter((f) => hasCoords(f) && spotKey(f) === key);
        here.sort((a, b) => (a.id === firm.id ? -1 : b.id === firm.id ? 1 : 0));

        const card = el('div', 'popup');
        const head = el('div', 'popup-head', here.length > 1 ? `이 위치의 기관 ${here.length}곳` : '기관 정보');
        const close = el('button', 'popup-close', '×');
        close.type = 'button';
        close.setAttribute('aria-label', '닫기');
        close.addEventListener('click', closePopup);
        head.append(close);

        const list = el('ul', 'popup-list');
        here.forEach((f) => {
            const item = el('li', f.id === firm.id ? 'is-current' : null);
            item.append(el('div', 'popup-name', f.name));
            const meta = el('div', 'popup-meta');
            meta.append(document.createTextNode([f.type, f.address].filter(Boolean).join(' · ')));
            item.append(meta);
            const allocation = allocationText(f);
            if (allocation) item.append(el('div', 'popup-allocation', allocation));
            list.append(item);
        });
        card.append(head, list);

        // Scrolling or dragging inside the card should not move the map.
        ['wheel', 'mousedown', 'touchstart', 'dblclick'].forEach((type) => {
            card.addEventListener(type, (event) => event.stopPropagation(), { passive: true });
        });

        const position = new kakao.maps.LatLng(firm.lat, firm.lng);
        popup.setContent(card);
        popup.setPosition(position);
        popup.setMap(map);
        revealPopup(position, card);
    }

    /** Pan just enough that the card above the marker is not cut off by the map's edge. */
    function revealPopup(position, card) {
        const container = document.getElementById('map');
        const projection = map.getProjection();
        const point = projection.containerPointFromCoords(position);
        // Measured once Kakao has drawn the card; the fallbacks cover a card not laid out yet.
        const cardHeight = (card.offsetHeight || 260) + 56; // card + marker + margin
        const halfWidth = (card.offsetWidth || 280) / 2 + 16;

        let dx = 0;
        let dy = 0;
        if (point.y < cardHeight) dy = point.y - cardHeight;
        if (point.x < halfWidth) dx = point.x - halfWidth;
        else if (point.x > container.clientWidth - halfWidth) dx = point.x - (container.clientWidth - halfWidth);
        if (!dx && !dy) return;

        const center = projection.containerPointFromCoords(map.getCenter());
        map.panTo(projection.coordsFromContainerPoint(new kakao.maps.Point(center.x + dx, center.y + dy)));
    }

    function selectFirm(id) {
        state.selectedId = id;
        markCurrent();
    }

    function focusFirm(firm) {
        selectFirm(firm.id);
        if (!map || !hasCoords(firm)) return;
        if (map.getLevel() > FOCUS_LEVEL) map.setLevel(FOCUS_LEVEL);
        // Jump (no animation) so the popup's position is measured against the final view.
        map.setCenter(new kakao.maps.LatLng(firm.lat, firm.lng));
        openPopup(firm);
        // Stacked layout: the map is above the list, so bring it into view.
        if (window.matchMedia('(max-width: 860px)').matches) {
            document.getElementById('map').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    // ------------------------------------------------------------- update

    function update({ fit = false } = {}) {
        const firms = filteredFirms();
        document.getElementById('filtered-count').textContent = firms.length.toLocaleString('ko-KR');
        renderList(firms);
        renderMarkers(firms, fit);
    }

    function showMapUnavailable() {
        // An unregistered domain and a network failure look the same from here.
        showMapMessage(
            '지도를 불러올 수 없습니다.',
            '이 사이트 주소가 카카오 디벨로퍼스에 등록되지 않았거나 네트워크 오류입니다. 목록은 그대로 볼 수 있습니다.',
        );
    }

    function startMap() {
        if (!window.ENABLE_KAKAO_MAP) return;
        if (typeof kakao === 'undefined' || !kakao.maps) {
            showMapUnavailable();
            return;
        }
        let loaded = false;
        const timer = setTimeout(() => {
            if (!loaded) showMapUnavailable();
        }, KAKAO_TIMEOUT_MS);
        // A slow load that finishes after the timeout still replaces the message.
        kakao.maps.load(() => {
            loaded = true;
            clearTimeout(timer);
            initMap();
            renderMarkers(filteredFirms(), true);
        });
    }

    // --------------------------------------------------------------- start

    document.addEventListener('DOMContentLoaded', () => {
        state.firms = typeof firmsData !== 'undefined' ? firmsData : [];
        document.getElementById('total-count').textContent = state.firms.length.toLocaleString('ko-KR');

        const source = typeof firmsDataSource !== 'undefined' ? String(firmsDataSource) : '';
        const year = source.match(/^(\d{4})/);
        document.getElementById('source-note').textContent = year
            ? `${year[1]}년 명단 · 위치는 근사값`
            : '위치는 근사값';

        buildRegionChips();
        buildGuOptions();

        document.getElementById('gu-select').addEventListener('change', (event) => {
            state.gu = event.target.value;
            update({ fit: true });
        });

        let searchTimer = null;
        document.getElementById('search-input').addEventListener('input', (event) => {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(() => {
                state.query = event.target.value.trim().toLowerCase();
                update({ fit: true });
            }, 250);
        });

        update();
        startMap();
    });
})();
