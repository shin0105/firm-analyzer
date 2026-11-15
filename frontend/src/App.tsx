import { useEffect, useRef, useState } from 'react';
import {
  BrowserRouter as Router,
  Routes,
  Route,
  NavLink,
  Navigate,
  useLocation,
  useNavigate,
  Link,
} from 'react-router-dom';
import {
  ChevronDown,
  Compass,
  FileText,
  House,
  Info,
  ListChecks,
  MapPinned,
  Moon,
  Play,
  Search,
  Settings,
  Sun,
  type LucideIcon,
} from 'lucide-react';
import Dashboard from './pages/Dashboard';
import FirmResults from './pages/FirmResults';
import ConfigPage from './pages/ConfigPage';
import SummaryViewer from './pages/SummaryViewer';
import Rosters from './pages/Rosters';
import Pipeline from './pages/Pipeline';
import About from './pages/About';
import { AiLine } from './components/AiNotice';
import { STATIC_SITE } from './lib/api';
import { cx } from './lib/format';
import { setTheme, useTheme } from './lib/theme';

interface NavItem {
  to: string;
  label: string;
  /** Under the icon in the phone tab bar. */
  short: string;
  /** For the browser tab. */
  title: string;
  icon: LucideIcon;
}

const PUBLIC_NAV: NavItem[] = [
  { to: '/', label: '개요', short: '개요', title: '개요', icon: House },
  { to: '/firms', label: '배정 지도', short: '지도', title: '인원배정 업체 지도', icon: MapPinned },
  { to: '/summary', label: '업체 요약', short: '업체', title: '업체 요약', icon: FileText },
  { to: '/about', label: '이용 안내', short: '안내', title: '이용 안내 및 면책 조항', icon: Info },
];

/** These change files or start jobs, so the static build leaves them out. */
const ADMIN_NAV: NavItem[] = STATIC_SITE
  ? []
  : [
      { to: '/rosters', label: '명단 관리', short: '명단', title: '전문연 명단 관리', icon: ListChecks },
      { to: '/pipeline', label: '파이프라인 실행', short: '실행', title: '파이프라인 실행', icon: Play },
      { to: '/config', label: '설정', short: '설정', title: '설정 변경', icon: Settings },
    ];

/** Pages sized to the viewport so their panes scroll instead of the page. */
function fillMode(pathname: string): 'all' | 'desktop' | null {
  if (pathname === '/firms') return 'all';
  if (pathname === '/summary') return 'desktop';
  return null;
}

function NotFound() {
  return (
    <div className="card mx-auto grid max-w-md justify-items-start gap-5">
      <div>
        <h1 className="page-title">페이지를 찾을 수 없어요</h1>
        <p className="page-subtitle">주소가 바뀌었거나 없는 페이지예요.</p>
      </div>
      <Link className="btn btn-primary" to="/">
        <Compass size={18} strokeWidth={1.75} aria-hidden="true" />
        개요로 가기
      </Link>
    </div>
  );
}

function ThemeToggle() {
  const theme = useTheme();
  const next = theme === 'dark' ? 'light' : 'dark';
  const label = next === 'dark' ? '어두운 화면으로 보기' : '밝은 화면으로 보기';
  return (
    <button type="button" className="btn-icon" onClick={() => setTheme(next)} aria-label={label} title={label}>
      {theme === 'dark' ? (
        <Sun size={18} strokeWidth={1.75} aria-hidden="true" />
      ) : (
        <Moon size={18} strokeWidth={1.75} aria-hidden="true" />
      )}
    </button>
  );
}

/** The local-only pages, kept out of the main row under one 관리 menu. */
function AdminMenu({ align }: { align: 'left' | 'right' }) {
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const active = ADMIN_NAV.some((item) => item.to === pathname);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      setOpen(false);
      buttonRef.current?.focus();
    };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  return (
    <div className="relative" ref={rootRef}>
      <button
        ref={buttonRef}
        type="button"
        className={cx('nav-link', active && 'is-active')}
        aria-expanded={open}
        aria-controls={`admin-menu-${align}`}
        onClick={() => setOpen((value) => !value)}
      >
        관리
        <ChevronDown size={14} strokeWidth={2} aria-hidden="true" />
      </button>
      {open && (
        <ul
          id={`admin-menu-${align}`}
          className={cx(
            'absolute top-full z-40 mt-2 grid w-52 gap-0.5 rounded-[14px] bg-card p-1.5',
            'shadow-[0_10px_30px_rgb(25_31_40/0.16),0_0_0_1px_var(--color-line)]',
            align === 'left' ? 'left-0' : 'right-0',
          )}
        >
          {ADMIN_NAV.map(({ to, label, icon: Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  cx(
                    'flex items-center gap-2.5 rounded-[10px] px-3 py-2 text-sm',
                    isActive ? 'bg-pen-tint font-semibold text-pen' : 'text-ink-2 hover:bg-canvas hover:text-ink',
                  )
                }
              >
                <Icon size={16} strokeWidth={1.75} aria-hidden="true" />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Desktop search: sends the query to 업체 요약. */
function GlobalSearch() {
  const navigate = useNavigate();
  const [value, setValue] = useState('');
  return (
    <form
      role="search"
      className="hidden md:block"
      onSubmit={(event) => {
        event.preventDefault();
        const q = value.trim();
        navigate(q ? `/summary?q=${encodeURIComponent(q)}` : '/summary', { state: { focusSearch: !q } });
        setValue('');
      }}
    >
      <label htmlFor="global-search" className="visually-hidden">
        업체 이름이나 요약 내용으로 찾기
      </label>
      <div className="flex h-9 w-48 items-center gap-2 rounded-[10px] bg-canvas pr-1.5 pl-3 text-meta focus-within:outline-2 focus-within:outline-pen lg:w-64">
        <Search size={16} strokeWidth={1.75} aria-hidden="true" />
        <input
          id="global-search"
          type="search"
          enterKeyHint="search"
          autoComplete="off"
          placeholder="업체 이름이나 키워드"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          className="h-full min-w-0 flex-1 bg-transparent text-[13.5px] text-ink placeholder:text-meta focus-visible:outline-none"
        />
        <kbd className="kbd" aria-hidden="true">
          /
        </kbd>
      </div>
    </form>
  );
}

function TopBar({ pathname, wide }: { pathname: string; wide: boolean }) {
  const onSummary = pathname === '/summary';
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-card">
      <div
        className={cx(
          'mx-auto flex h-14 w-full items-center gap-3 px-4 md:gap-6 md:px-6',
          wide ? 'max-w-[1440px]' : 'max-w-[1160px]',
        )}
      >
        <Link to="/" className="flex items-baseline gap-2 whitespace-nowrap">
          <span className="text-base font-extrabold tracking-[-0.02em]">Firm Analyzer</span>
          <span className="hidden font-mono text-[11px] text-meta lg:inline">전문연 업체 노트</span>
        </Link>

        <nav aria-label="주요 메뉴" className="hidden md:block">
          <ul className="flex items-center gap-0.5">
            {PUBLIC_NAV.map(({ to, label }) => (
              <li key={to}>
                <NavLink to={to} end={to === '/'} className={({ isActive }) => cx('nav-link', isActive && 'is-active')}>
                  {label}
                </NavLink>
              </li>
            ))}
            {ADMIN_NAV.length > 0 && (
              <li>
                <AdminMenu align="left" />
              </li>
            )}
          </ul>
        </nav>

        <div className="ml-auto flex items-center gap-1">
          {/* 업체 요약 has its own search field; elsewhere this one sends you there. */}
          {!onSummary && <GlobalSearch />}
          {!onSummary && (
            <Link
              to="/summary"
              state={{ focusSearch: true }}
              className="btn-icon md:hidden"
              aria-label="업체 찾기"
            >
              <Search size={19} strokeWidth={1.75} aria-hidden="true" />
            </Link>
          )}
          <ThemeToggle />
          {ADMIN_NAV.length > 0 && (
            <div className="md:hidden">
              <AdminMenu align="right" />
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

function BottomTabs() {
  return (
    <nav
      aria-label="주요 메뉴"
      className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-card pb-[env(safe-area-inset-bottom)] md:hidden"
    >
      <ul className="grid grid-cols-4">
        {PUBLIC_NAV.map(({ to, short, icon: Icon }) => (
          <li key={to}>
            <NavLink
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                cx(
                  'flex flex-col items-center gap-0.5 pt-2 pb-2 text-[11px] leading-tight',
                  isActive ? 'font-bold text-ink' : 'text-meta',
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icon size={22} strokeWidth={isActive ? 2.25 : 1.75} aria-hidden="true" />
                  {short}
                </>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function Shell() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const fill = fillMode(pathname);

  // Keep the tab title in sync so history and bookmarks are meaningful.
  useEffect(() => {
    const current = [...PUBLIC_NAV, ...ADMIN_NAV].find((item) => item.to === pathname);
    document.title = current ? `${current.title} · Firm Analyzer` : 'Firm Analyzer';
  }, [pathname]);

  // "/" searches from any page, unless the user is already typing.
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== '/' || event.metaKey || event.ctrlKey || event.altKey || event.isComposing) return;
      const target = event.target as HTMLElement | null;
      if (target && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName))) return;
      event.preventDefault();
      const field = ['firm-search', 'global-search']
        .map((id) => document.getElementById(id) as HTMLInputElement | null)
        .find((input) => input && input.offsetParent !== null);
      if (field) {
        field.focus();
        field.select();
      } else {
        navigate('/summary', { state: { focusSearch: true } });
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [navigate]);

  return (
    <div
      className={cx(
        'flex min-h-dvh flex-col pb-[calc(3.75rem+env(safe-area-inset-bottom))] md:pb-0',
        fill === 'all' && 'h-dvh',
        fill === 'desktop' && 'lg:h-dvh',
      )}
    >
      <a className="skip-link" href="#main-content">
        본문으로 건너뛰기
      </a>

      <TopBar pathname={pathname} wide={fill !== null} />

      <main
        id="main-content"
        tabIndex={-1}
        className={cx(
          'flex-1 outline-none',
          // Graph paper behind the cards; on phones only on the home screen.
          pathname === '/' ? 'bg-graph' : 'md:bg-graph',
          fill === 'all' && 'min-h-0',
          fill === 'desktop' && 'lg:min-h-0',
        )}
      >
        <div
          className={cx(
            'mx-auto w-full px-4 py-5 md:px-6 md:py-7',
            fill ? 'max-w-[1440px]' : 'max-w-[1160px]',
            fill === 'all' && 'h-full',
            fill === 'desktop' && 'lg:h-full',
          )}
        >
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
        </div>
      </main>

      {/* The map shows the 병무청 list itself, nothing AI-written. */}
      {pathname !== '/firms' && (
        <footer className="border-t border-line">
          <div className={cx('mx-auto w-full px-4 py-3.5 md:px-6', fill ? 'max-w-[1440px]' : 'max-w-[1160px]')}>
            <AiLine />
          </div>
        </footer>
      )}

      <BottomTabs />
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
