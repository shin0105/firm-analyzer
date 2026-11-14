import { useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { apiUrl } from '../lib/api';
import { LoadingState } from '../components/States';

export default function FirmResults() {
  const [loaded, setLoaded] = useState(false);
  const mapUrl = apiUrl('/map');

  return (
    <div className="glass-card page-fill">
      <div className="header-row">
        <div className="page-header">
          <h2 className="page-title">기업 검색 결과</h2>
          <p className="page-subtitle">지도 기반 기업 뷰어</p>
        </div>
        {/* The embedded map is cramped on small screens — offer a full window. */}
        <a
          className="btn btn-secondary btn-sm"
          href={mapUrl}
          target="_blank"
          rel="noopener noreferrer"
        >
          <ExternalLink size={16} aria-hidden="true" />
          새 창에서 열기
        </a>
      </div>

      <div className="frame-wrapper">
        {!loaded && (
          <div className="frame-overlay">
            <LoadingState message="지도를 불러오는 중..." />
          </div>
        )}
        <iframe src={mapUrl} title="기업 지도 뷰어" onLoad={() => setLoaded(true)} />
      </div>
    </div>
  );
}
