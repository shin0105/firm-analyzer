import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ExternalLink } from 'lucide-react';
import { mapUrl } from '../lib/data';
import { useTheme } from '../lib/theme';
import { LoadingState } from '../components/States';

function withParams(url: string, params: URLSearchParams): string {
  const query = params.toString();
  return query ? `${url}${url.includes('?') ? '&' : '?'}${query}` : url;
}

/** The iframe and its loading cover; keyed by URL so a new URL starts covered again. */
function MapFrame({ src }: { src: string }) {
  const [loaded, setLoaded] = useState(false);
  return (
    <div className="relative min-h-[420px] flex-1 overflow-hidden rounded-card bg-card">
      {!loaded && (
        <div className="absolute inset-0 grid place-items-center bg-card">
          <LoadingState message="지도를 불러오는 중..." />
        </div>
      )}
      <iframe src={src} title="인원배정 업체 지도" onLoad={() => setLoaded(true)} className="block h-full w-full border-0" />
    </div>
  );
}

export default function FirmResults() {
  const theme = useTheme();
  const [searchParams] = useSearchParams();

  // `region` and `q` come from links on 개요 and 업체 요약; the map page reads them.
  const shared = new URLSearchParams();
  for (const key of ['region', 'q']) {
    const value = searchParams.get(key)?.trim();
    if (value) shared.set(key, value);
  }
  const standaloneUrl = withParams(mapUrl, shared);
  // `embed=1` drops the map page's own header; `theme` keeps it in step with the app.
  const embedded = new URLSearchParams(shared);
  embedded.set('embed', '1');
  embedded.set('theme', theme);
  const frameUrl = withParams(mapUrl, embedded);

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="header-row mb-0">
        <div className="page-header">
          <h1 className="page-title">배정 지도</h1>
          <p className="page-subtitle">병무청 전문연구요원 인원배정 현황이에요. 위치는 주소로 추정한 근사값이에요.</p>
        </div>
        {/* The embedded map is cramped on small screens: offer a full window. */}
        <a className="btn btn-secondary btn-sm" href={standaloneUrl} target="_blank" rel="noopener noreferrer">
          <ExternalLink size={15} strokeWidth={1.75} aria-hidden="true" />
          새 창에서 열기
        </a>
      </div>
      <MapFrame key={frameUrl} src={frameUrl} />
    </div>
  );
}
