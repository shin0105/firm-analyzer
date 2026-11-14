import { useEffect, useState } from 'react';
import {
  BrowserRouter as Router,
  Routes,
  Route,
  NavLink,
  Navigate,
  useLocation,
  Link,
} from 'react-router-dom';
import {
  LayoutDashboard,
  Map,
  Settings,
  FileText,
  Info,
  ListChecks,
  Menu,
  X,
  Compass,
  Play,
} from 'lucide-react';
import Dashboard from './pages/Dashboard';
import FirmResults from './pages/FirmResults';
import ConfigPage from './pages/ConfigPage';
import SummaryViewer from './pages/SummaryViewer';
import Rosters from './pages/Rosters';
import Pipeline from './pages/Pipeline';
import About from './pages/About';
import { STATIC_SITE } from './lib/api';

/** `needsServer` pages change files or start jobs, so the static build leaves them out. */
const NAV_ITEMS = [
  { to: '/', label: '대시보드', icon: LayoutDashboard, title: '대시보드', needsServer: false },
  { to: '/rosters', label: '전문연 명단 관리', icon: ListChecks, title: '전문연 명단 관리', needsServer: true },
  { to: '/pipeline', label: '파이프라인 실행', icon: Play, title: '파이프라인 실행', needsServer: true },
  { to: '/firms', label: '기업 검색 결과', icon: Map, title: '기업 검색 결과', needsServer: false },
  { to: '/summary', label: '요약 결과 보기', icon: FileText, title: '요약 결과 보기', needsServer: false },
  { to: '/config', label: '설정 변경', icon: Settings, title: '설정 변경', needsServer: true },
  { to: '/about', label: '이용 안내', icon: Info, title: '이용 안내 및 면책 조항', needsServer: false },
] as const;

const VISIBLE_NAV = NAV_ITEMS.filter((item) => !(STATIC_SITE && item.needsServer));

function NotFound() {
  return (
    <div className="glass-card">
      <div className="page-header">
        <h2 className="page-title">페이지를 찾을 수 없습니다</h2>
        <p className="page-subtitle">요청하신 주소가 존재하지 않습니다.</p>
      </div>
      <Link className="btn btn-primary" to="/">
        <Compass size={18} aria-hidden="true" />
        대시보드로 이동
      </Link>
    </div>
  );
}

function Shell() {
  const location = useLocation();
  const [navOpen, setNavOpen] = useState(false);

  // Keep the tab title in sync so history and bookmarks are meaningful.
  useEffect(() => {
    const current = VISIBLE_NAV.find((item) => item.to === location.pathname);
    document.title = current
      ? `${current.title} · Firm Analyzer`
      : 'Firm Analyzer';
  }, [location.pathname]);

  // Escape closes the drawer, as expected from any overlay.
  useEffect(() => {
    if (!navOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setNavOpen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [navOpen]);

  return (
    <div className="app-container">
      <a className="skip-link" href="#main-content">
        본문으로 건너뛰기
      </a>

      <header className="mobile-header">
        <button
          type="button"
          className="btn-icon"
          onClick={() => setNavOpen((open) => !open)}
          aria-expanded={navOpen}
          aria-controls="primary-navigation"
          aria-label={navOpen ? '메뉴 닫기' : '메뉴 열기'}
        >
          {navOpen ? <X size={22} aria-hidden="true" /> : <Menu size={22} aria-hidden="true" />}
        </button>
        <span className="sidebar-brand">Firm Analyzer</span>
      </header>

      {navOpen && (
        <button
          type="button"
          className="nav-scrim"
          aria-label="메뉴 닫기"
          onClick={() => setNavOpen(false)}
        />
      )}

      <aside className="sidebar" id="primary-navigation" data-open={navOpen}>
        <div className="sidebar-brand">Firm Analyzer</div>
        <button
          type="button"
          className="btn-icon nav-close"
          onClick={() => setNavOpen(false)}
          aria-label="메뉴 닫기"
        >
          <X size={20} aria-hidden="true" />
        </button>
        <nav className="nav-links" aria-label="주요 메뉴">
          {VISIBLE_NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}
              onClick={() => setNavOpen(false)}
            >
              {({ isActive }) => (
                <>
                  <Icon size={20} aria-hidden="true" />
                  <span>{label}</span>
                  {isActive && <span className="visually-hidden">(현재 페이지)</span>}
                </>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          기업 분석 및 요약 도구
          <br />
          요약은 AI가 생성한 참고 자료입니다.{' '}
          <Link to="/about" onClick={() => setNavOpen(false)}>
            이용 안내
          </Link>
        </div>
      </aside>

      <main className="main-content" id="main-content" tabIndex={-1}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/firms" element={<FirmResults />} />
          <Route path="/summary" element={<SummaryViewer />} />
          <Route path="/about" element={<About />} />
          {!STATIC_SITE && (
            <>
              <Route path="/pipeline" element={<Pipeline />} />
              <Route path="/config" element={<ConfigPage />} />
              <Route path="/rosters" element={<Rosters />} />
              {/* The PDF OCR page became the AI option of 명단 가져오기. */}
              <Route path="/ocr" element={<Navigate to="/rosters" replace />} />
            </>
          )}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Router>
      <Shell />
    </Router>
  );
}
