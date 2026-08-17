import { apiUrl } from '../api';


export default function FirmResults() {
  return (
    <div className="glass-card" style={{ height: 'calc(100vh - 5rem)', display: 'flex', flexDirection: 'column' }}>
      <h2 className="page-title">기업 검색 결과</h2>
      <p className="page-subtitle">지도 기반 기업 뷰어</p>
      
      <div style={{ flex: 1, borderRadius: '1rem', overflow: 'hidden', border: '1px solid var(--surface-border)' }}>
        <iframe 
          src={apiUrl('/firms')} 
          style={{ width: '100%', height: '100%', border: 'none' }}
          title="Firm Viewer"
        />
      </div>
    </div>
  );
}
