import { useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { mapUrl } from '../lib/data';
import { LoadingState } from '../components/States';

/** `?embed=1` drops the map page's own header and frame inside the app. */
const embeddedMapUrl = `${mapUrl}${mapUrl.includes('?') ? '&' : '?'}embed=1`;

export default function FirmResults() {
  const [loaded, setLoaded] = useState(false);
  return (
    <div className="glass-card page-fill">
      <div className="header-row">
        <div className="page-header">
          <h2 className="page-title">인원배정 업체 지도</h2>
          <p className="page-subtitle">
            병무청 전문연구요원 인원배정 현황 · 위치는 주소로 추정한 근사값입니다
          </p>
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
        <iframe src={embeddedMapUrl} title="인원배정 업체 지도" onLoad={() => setLoaded(true)} />
      </div>
    </div>
  );
}
