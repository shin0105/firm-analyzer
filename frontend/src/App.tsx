import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import { LayoutDashboard, Map, Settings, FileText, FileUp } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import FirmResults from './pages/FirmResults';
import ConfigPage from './pages/ConfigPage';
import SummaryViewer from './pages/SummaryViewer';
import OcrUpload from './pages/OcrUpload';

function App() {
  return (
    <Router>
      <div className="app-container">
        <aside className="sidebar">
          <h1>Firm Analyzer</h1>
          <nav className="nav-links">
            <NavLink to="/" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
              <LayoutDashboard size={20} />
              <span>대시보드</span>
            </NavLink>
            <NavLink to="/firms" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
              <Map size={20} />
              <span>기업 검색 결과</span>
            </NavLink>
            <NavLink to="/summary" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
              <FileText size={20} />
              <span>요약 결과 보기</span>
            </NavLink>
            <NavLink to="/ocr" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
              <FileUp size={20} />
              <span>PDF OCR 변환</span>
            </NavLink>
            <NavLink to="/config" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
              <Settings size={20} />
              <span>설정 변경</span>
            </NavLink>
          </nav>
        </aside>
        
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/firms" element={<FirmResults />} />
            <Route path="/config" element={<ConfigPage />} />
            <Route path="/summary" element={<SummaryViewer />} />
            <Route path="/ocr" element={<OcrUpload />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
