import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ChevronRight, FileText, Search, X } from 'lucide-react';
import { api } from '../lib/api';
import { useAsync } from '../lib/useAsync';
import {
  parseResultsSummary,
  type FirmDetail,
  type FirmListItem,
  type FirmListResponse,
  type FirmQuery,
  type ResultsSummaryResponse,
  type Taxonomy,
  type TaxonomySector,
} from '../lib/types';
import { EmptyState, ErrorState, LoadingState, Spinner } from '../components/States';
import Markdown from '../components/Markdown';

/** How long typing must pause before the search reaches the URL and the API. */
const SEARCH_DEBOUNCE_MS = 250;

/** The open firm, addressed the way `GET /api/firms/:category/:name` expects. */
interface Selection {
  categoryId: string;
  name: string;
}

function SectorBadge({
  sectorId,
  confidence,
  sector,
}: {
  sectorId: string | null;
  confidence?: string | null;
  sector?: TaxonomySector;
}) {
  if (!sectorId) {
    return <span className="sector-badge sector-badge--none">미분류</span>;
  }
  return (
    <span
      className="sector-badge"
      style={{ '--badge-color': sector?.color ?? '#64748b' } as CSSProperties}
      data-confidence={confidence ?? undefined}
      title={confidence ? `섹터 확신도: ${confidence}` : undefined}
    >
      {sector?.name ?? sectorId}
    </span>
  );
}

/** `text` with the first case-insensitive occurrence of `term` marked. */
function Highlight({ text, term }: { text: string; term: string }) {
  const needle = term.trim().toLowerCase();
  const at = needle ? text.toLowerCase().indexOf(needle) : -1;
  if (at < 0) return <>{text}</>;
  return (
    <>
      {text.slice(0, at)}
      <mark>{text.slice(at, at + needle.length)}</mark>
      {text.slice(at + needle.length)}
    </>
  );
}

export default function SummaryViewer() {
  // Category, search and filters all live in the URL so a view is linkable
  // and the dashboard can jump straight to a category.
  const [searchParams, setSearchParams] = useSearchParams();
  const categoryParam = searchParams.get('category') ?? '';
  const qParam = searchParams.get('q') ?? '';
  const sectorParam = searchParams.get('sector') ?? '';
  const verticalParam = searchParams.get('vertical') ?? '';
  const segmentedOnly = searchParams.get('segmented') === 'true';

  const updateParams = useCallback(
    (patch: Record<string, string>) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          for (const [key, value] of Object.entries(patch)) {
            if (value) next.set(key, value);
            else next.delete(key);
          }
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  // The input answers every keystroke; the URL, and so the request, follows
  // once typing pauses. A URL change from elsewhere (back/forward, reset)
  // rewrites the input.
  const [draft, setDraft] = useState(qParam);
  const [syncedQ, setSyncedQ] = useState(qParam);
  if (qParam !== syncedQ) {
    setSyncedQ(qParam);
    setDraft(qParam);
  }
  useEffect(() => {
    const next = draft.trim() ? draft : '';
    if (next === qParam) return;
    const timer = window.setTimeout(() => updateParams({ q: next }), SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [draft, qParam, updateParams]);

  const summary = useAsync(async () => {
    const res = await api.get<ResultsSummaryResponse>('/api/results/summary');
    return parseResultsSummary(res.data);
  });
  const categories = useMemo(() => summary.data?.categories ?? [], [summary.data]);

  const taxonomy = useAsync(async () => (await api.get<Taxonomy>('/api/taxonomy')).data);
  const sectors = useMemo(() => taxonomy.data?.sectors ?? [], [taxonomy.data]);
  const sectorById = useMemo(() => new Map(sectors.map((s) => [s.id, s])), [sectors]);
  // "none" is never stored on a firm, so filtering by it could only come up empty.
  const verticals = useMemo(
    () => (taxonomy.data?.verticals ?? []).filter((v) => v.id !== 'none'),
    [taxonomy.data],
  );

  // A stale bookmark can name an id that no longer exists, which the API
  // rejects. Once the valid ids are known, such a value is treated as unset.
  const category = summary.data
    ? categories.some((c) => c.id === categoryParam)
      ? categoryParam
      : ''
    : categoryParam;
  const sector = taxonomy.data ? (sectorById.has(sectorParam) ? sectorParam : '') : sectorParam;
  const vertical = taxonomy.data
    ? verticals.some((v) => v.id === verticalParam)
      ? verticalParam
      : ''
    : verticalParam;
  // Hold the request until those ids are known, instead of sending one the
  // API would reject.
  const idsPending =
    (summary.status === 'loading' && Boolean(categoryParam)) ||
    (taxonomy.status === 'loading' && Boolean(sectorParam || verticalParam));
  const searchTerm = qParam.trim();
  const filtering = Boolean(searchTerm || sector || vertical || segmentedOnly);

  const firmQuery: FirmQuery = {
    q: searchTerm || undefined,
    category: category || undefined,
    sector: sector || undefined,
    vertical: vertical || undefined,
    segmented: segmentedOnly ? 'true' : undefined,
  };
  const firms = useAsync(
    async () => {
      if (idsPending) return null;
      return (await api.get<FirmListResponse>('/api/firms', { params: firmQuery })).data;
    },
    [idsPending, firmQuery.q, firmQuery.category, firmQuery.sector, firmQuery.vertical, firmQuery.segmented],
  );

  // Keep the previous result on screen while a refined search loads, rather
  // than flashing a spinner on every pause in typing.
  const [shownFirms, setShownFirms] = useState<FirmListResponse | null>(null);
  if (firms.data && firms.data !== shownFirms) {
    setShownFirms(firms.data);
  }
  const list = firms.status === 'error' ? null : (firms.data ?? shownFirms);
  const listLoading = firms.status === 'loading' || idsPending;
  const refreshing = listLoading && list !== null;

  const [selected, setSelected] = useState<Selection | null>(null);
  // Full summaries are fetched one at a time, only for the firm being read.
  const detail = useAsync(async () => {
    if (!selected) return null;
    const path = `/api/firms/${encodeURIComponent(selected.categoryId)}/${encodeURIComponent(selected.name)}`;
    return (await api.get<FirmDetail>(path)).data;
  }, [selected?.categoryId, selected?.name]);

  const summaryPaneRef = useRef<HTMLElement>(null);

  const selectFirm = (firm: FirmListItem) => {
    setSelected({ categoryId: firm.category_id, name: firm.name });
    // Stacked on narrow screens the summary sits below the fold, so bring it
    // into view rather than leaving the tap looking like it did nothing.
    if (window.matchMedia('(max-width: 1024px)').matches) {
      summaryPaneRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const resetFilters = () => {
    setDraft('');
    updateParams({ q: '', sector: '', vertical: '', segmented: '' });
  };

  const detailSector = detail.data?.segmentation?.sector ?? null;

  return (
    <div className="page-fill">
      <div className="page-header">
        <h2 className="page-title">요약 결과 보기</h2>
        <p className="page-subtitle">전체 카테고리에서 기업을 검색하고 세분류로 좁혀 봅니다</p>
      </div>

      <div className="split-view">
        <section className="glass-card split-pane" aria-label="기업 목록">
          {summary.status === 'loading' && <LoadingState message="카테고리를 불러오는 중..." />}
          {summary.status === 'error' && (
            <ErrorState message={summary.error ?? ''} onRetry={summary.reload} />
          )}

          {summary.status === 'success' && (
            <>
              <div className="chip-row" role="group" aria-label="카테고리 선택">
                <button
                  type="button"
                  className="chip"
                  aria-pressed={!category}
                  onClick={() => updateParams({ category: '' })}
                >
                  전체
                  <span className="chip-count">{summary.data?.total ?? 0}</span>
                </button>
                {categories.map((cat) => (
                  <button
                    key={cat.id}
                    type="button"
                    className="chip"
                    aria-pressed={category === cat.id}
                    onClick={() => updateParams({ category: cat.id })}
                  >
                    <span className="stat-dot" style={{ background: cat.color }} aria-hidden="true" />
                    {cat.name}
                    <span className="chip-count">{cat.count}</span>
                  </button>
                ))}
              </div>

              <div className="form-group search-field" style={{ marginBottom: '0.75rem' }}>
                <label className="visually-hidden" htmlFor="firm-search">
                  기업 이름 또는 요약 내용 검색
                </label>
                <Search size={16} aria-hidden="true" />
                <input
                  id="firm-search"
                  className="form-input"
                  type="search"
                  placeholder="기업 이름 또는 요약 내용 검색..."
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                />
              </div>

              <div className="filter-row" role="group" aria-label="세분류 필터">
                <label className="visually-hidden" htmlFor="filter-sector">
                  산업 섹터
                </label>
                <select
                  id="filter-sector"
                  className="form-input"
                  value={sector}
                  onChange={(e) => updateParams({ sector: e.target.value })}
                  disabled={!taxonomy.data}
                >
                  <option value="">모든 섹터</option>
                  {sectors.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </select>

                <label className="visually-hidden" htmlFor="filter-vertical">
                  기술 버티컬
                </label>
                <select
                  id="filter-vertical"
                  className="form-input"
                  value={vertical}
                  onChange={(e) => updateParams({ vertical: e.target.value })}
                  disabled={!taxonomy.data}
                >
                  <option value="">모든 기술 버티컬</option>
                  {verticals.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name}
                    </option>
                  ))}
                </select>

                <button
                  type="button"
                  className="chip"
                  aria-pressed={segmentedOnly}
                  onClick={() => updateParams({ segmented: segmentedOnly ? '' : 'true' })}
                >
                  세분류된 기업만
                </button>

                {filtering && (
                  <button type="button" className="btn btn-ghost btn-sm" onClick={resetFilters}>
                    <X size={16} aria-hidden="true" />
                    초기화
                  </button>
                )}
              </div>

              {taxonomy.status === 'error' && (
                <p className="form-hint" style={{ marginBottom: '0.75rem' }}>
                  세분류 목록을 불러오지 못해 섹터·버티컬 필터를 쓸 수 없습니다.
                </p>
              )}

              <div className="form-hint list-status" style={{ marginBottom: '0.75rem' }} aria-live="polite">
                {list &&
                  (filtering ? `${list.count}개 / 전체 ${list.total}개` : `전체 ${list.total}개`)}
                {refreshing && <Spinner small label="검색 중" />}
              </div>

              <div className="scroll-area">
                {listLoading && !list && (
                  <LoadingState message="기업 목록을 불러오는 중..." />
                )}
                {firms.status === 'error' && (
                  <ErrorState message={firms.error ?? ''} onRetry={firms.reload} />
                )}

                {list && list.firms.length === 0 && (
                  <EmptyState
                    title={filtering ? '조건에 맞는 기업이 없습니다' : '해당 카테고리에 기업이 없습니다'}
                    hint={filtering ? '검색어나 필터를 바꾸거나 초기화해 보세요.' : undefined}
                  />
                )}

                {list && list.firms.length > 0 && (
                  <ul className="firm-list" aria-label="기업 목록" aria-busy={refreshing}>
                    {list.firms.map((firm) => (
                      <li key={`${firm.category_id}/${firm.name}`}>
                        <button
                          type="button"
                          className="firm-item"
                          aria-current={
                            selected?.categoryId === firm.category_id && selected?.name === firm.name
                          }
                          onClick={() => selectFirm(firm)}
                        >
                          <span className="firm-item-main">
                            <span className="firm-item-name">{firm.name}</span>
                            <span className="firm-item-meta">
                              <SectorBadge
                                sectorId={firm.sector}
                                confidence={firm.sector_confidence}
                                sector={firm.sector ? sectorById.get(firm.sector) : undefined}
                              />
                              {!category && (
                                <span className="firm-item-category">{firm.category}</span>
                              )}
                            </span>
                            {firm.snippet && (
                              <span className="firm-item-snippet">
                                <Highlight text={firm.snippet} term={searchTerm} />
                              </span>
                            )}
                          </span>
                          <ChevronRight size={16} aria-hidden="true" />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </section>

        <section className="glass-card split-pane" aria-label="기업 요약" ref={summaryPaneRef}>
          {selected ? (
            <>
              <div className="header-row" style={{ marginBottom: '1rem' }}>
                <div className="firm-detail-heading">
                  <h3 className="section-title">{selected.name}</h3>
                  {detail.data && (
                    <span className="firm-item-meta">
                      <SectorBadge
                        sectorId={detailSector}
                        confidence={detail.data.segmentation?.confidence?.sector}
                        sector={detailSector ? sectorById.get(detailSector) : undefined}
                      />
                      <span className="firm-item-category">{detail.data.category}</span>
                    </span>
                  )}
                </div>
                <button type="button" className="btn btn-ghost btn-sm" onClick={() => setSelected(null)}>
                  <X size={16} aria-hidden="true" />
                  닫기
                </button>
              </div>
              <div className="scroll-area">
                {detail.status === 'loading' && <LoadingState message="요약을 불러오는 중..." />}
                {detail.status === 'error' && (
                  <ErrorState message={detail.error ?? ''} onRetry={detail.reload} />
                )}
                {detail.status === 'success' &&
                  detail.data &&
                  (detail.data.summary.trim() ? (
                    <Markdown content={detail.data.summary} />
                  ) : (
                    <EmptyState
                      title="요약 내용이 없습니다"
                      hint="이 기업에는 아직 summary.md 파일이 없습니다."
                    />
                  ))}
              </div>
            </>
          ) : (
            <EmptyState
              icon={<FileText size={28} aria-hidden="true" />}
              title="기업을 선택하세요"
              hint="왼쪽 목록에서 기업을 선택하면 요약이 표시됩니다."
            />
          )}
        </section>
      </div>
    </div>
  );
}
