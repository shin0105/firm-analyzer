import { Link, useNavigate } from 'react-router-dom';
import { Building2, Download, Play, RotateCw } from 'lucide-react';
import { STATIC_SITE } from '../lib/api';
import { exportCsvUrl, getResultsSummary } from '../lib/data';
import { useAsync } from '../lib/useAsync';
import { parseResultsSummary } from '../lib/types';
import { EmptyState, ErrorState } from '../components/States';
import AiNotice from '../components/AiNotice';

function StatSkeleton() {
  return (
    <div className="glass-card card-tight" aria-hidden="true">
      <div className="skeleton" style={{ height: '1rem', width: '55%' }} />
      <div className="skeleton" style={{ height: '2rem', width: '35%', marginTop: '0.75rem' }} />
      <div className="skeleton" style={{ height: '0.375rem', marginTop: '0.85rem' }} />
    </div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { status, data, error, reload } = useAsync(async () =>
    parseResultsSummary(await getResultsSummary()),
  );

  const categories = data?.categories ?? [];
  const total = data?.total ?? 0;
  const maxCount = Math.max(1, ...categories.map((c) => c.count));

  return (
    <div>
      <div className="header-row">
        <div className="page-header">
          <h2 className="page-title">대시보드</h2>
          <p className="page-subtitle">기업 분석 시스템 개요</p>
        </div>
        <div className="button-row">
          {/* Every result folder with segmentation columns: rebuilt by Flask, or the snapshot's copy. */}
          <a className="btn btn-secondary btn-sm" href={exportCsvUrl} download>
            <Download size={16} aria-hidden="true" />
            CSV 내보내기
          </a>
          {/* The static site's data only changes with a new deploy. */}
          {!STATIC_SITE && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={reload}
              disabled={status === 'loading'}
            >
              <RotateCw size={16} aria-hidden="true" />
              새로고침
            </button>
          )}
        </div>
      </div>

      <AiNotice compact />

      {status === 'error' && (
        <div className="glass-card">
          <ErrorState message={error ?? ''} onRetry={reload} />
        </div>
      )}

      {status === 'loading' && (
        <>
          <span className="visually-hidden" role="status">
            대시보드를 불러오는 중입니다
          </span>
          <div className="dashboard-grid">
            <StatSkeleton />
            <StatSkeleton />
            <StatSkeleton />
          </div>
        </>
      )}

      {status === 'success' && (
        <>
          <div className="glass-card" style={{ marginBottom: '1.5rem' }}>
            <div className="stat-card-label">
              <Building2 size={18} aria-hidden="true" />
              분석된 총 기업 수
            </div>
            <div className="dashboard-stat">
              {total.toLocaleString('ko-KR')}
              <span className="stat-card-unit">개</span>
            </div>
          </div>

          <h3 className="section-title" style={{ marginBottom: '1rem' }}>
            카테고리별 분포
          </h3>

          {categories.length === 0 ? (
            <div className="glass-card">
              <EmptyState
                title="분석된 기업이 없습니다"
                hint="필터와 검색·요약을 먼저 실행해 주세요."
              />
              {!STATIC_SITE && (
                <div style={{ display: 'flex', justifyContent: 'center' }}>
                  <Link className="btn btn-primary btn-sm" to="/pipeline">
                    <Play size={16} aria-hidden="true" />
                    파이프라인 실행으로 이동
                  </Link>
                </div>
              )}
            </div>
          ) : (
            <div className="dashboard-grid">
              {categories.map((cat) => (
                /* Each card doubles as a shortcut into that category's summaries. */
                <button
                  key={cat.id}
                  type="button"
                  className="glass-card glass-card--interactive card-tight stat-card"
                  onClick={() => navigate(`/summary?category=${encodeURIComponent(cat.id)}`)}
                  aria-label={`${cat.name} 카테고리 ${cat.count}개 기업 요약 보기`}
                >
                  <span className="stat-card-label">
                    <span className="stat-dot" style={{ background: cat.color }} aria-hidden="true" />
                    {cat.name}
                  </span>
                  <span className="stat-card-value">
                    {cat.count.toLocaleString('ko-KR')}
                    <span className="stat-card-unit">개</span>
                  </span>
                  <span className="stat-bar">
                    <span
                      className="stat-bar-fill"
                      style={{
                        width: `${Math.round((cat.count / maxCount) * 100)}%`,
                        background: cat.color,
                      }}
                    />
                  </span>
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
