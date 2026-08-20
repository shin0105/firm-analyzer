import { useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ChevronRight, FileText, Search, X } from 'lucide-react';
import { api } from '../lib/api';
import { useAsync } from '../lib/useAsync';
import {
  parseResultsSummary,
  type Firm,
  type FirmsResponse,
  type ResultsSummaryResponse,
} from '../lib/types';
import { EmptyState, ErrorState, LoadingState } from '../components/States';
import Markdown from '../components/Markdown';

export default function SummaryViewer() {
  // The selected category lives in the URL so the view is linkable and the
  // dashboard can jump straight to a category.
  const [searchParams, setSearchParams] = useSearchParams();
  const categoryParam = searchParams.get('category') ?? '';
  const [query, setQuery] = useState('');
  // Only the name is held in state; the firm object is looked up from the
  // current list, so a selection can never outlive the data it came from.
  const [selectedName, setSelectedName] = useState<string | null>(null);

  const summary = useAsync(async () => {
    const res = await api.get<ResultsSummaryResponse>('/api/results/summary');
    return parseResultsSummary(res.data).categories;
  });
  const categories = useMemo(() => summary.data ?? [], [summary.data]);

  // Fall back to the first category when the URL names none (or an unknown one).
  const activeCategory =
    categories.find((c) => c.id === categoryParam)?.id ?? categories[0]?.id ?? '';

  const selectCategory = (id: string) => {
    setSearchParams(id ? { category: id } : {}, { replace: true });
    setSelectedName(null);
    setQuery('');
  };

  const firms = useAsync(async () => {
    if (!activeCategory) return [] as Firm[];
    const res = await api.get<FirmsResponse>(`/api/results/${activeCategory}`);
    return res.data.firms ?? [];
  }, [activeCategory]);

  const firmList = useMemo(() => firms.data ?? [], [firms.data]);

  const filteredFirms = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return firmList;
    return firmList.filter((firm) => firm.name.toLowerCase().includes(needle));
  }, [firmList, query]);

  const selectedFirm: Firm | null =
    firmList.find((firm) => firm.name === selectedName) ?? null;

  const summaryPaneRef = useRef<HTMLElement>(null);

  const selectFirm = (name: string) => {
    setSelectedName(name);
    // Stacked on narrow screens the summary sits below the fold, so bring it
    // into view rather than leaving the tap looking like it did nothing.
    if (window.matchMedia('(max-width: 1024px)').matches) {
      summaryPaneRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <div className="page-fill">
      <div className="page-header">
        <h2 className="page-title">요약 결과 보기</h2>
        <p className="page-subtitle">카테고리별 기업 요약을 확인합니다</p>
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
                {categories.map((cat) => (
                  <button
                    key={cat.id}
                    type="button"
                    className="chip"
                    aria-pressed={activeCategory === cat.id}
                    onClick={() => selectCategory(cat.id)}
                  >
                    <span className="stat-dot" style={{ background: cat.color }} aria-hidden="true" />
                    {cat.name}
                    <span className="chip-count">{cat.count}</span>
                  </button>
                ))}
              </div>

              <div className="form-group search-field" style={{ marginBottom: '1rem' }}>
                <label className="visually-hidden" htmlFor="firm-search">
                  기업 이름 검색
                </label>
                <Search size={16} aria-hidden="true" />
                <input
                  id="firm-search"
                  className="form-input"
                  type="search"
                  placeholder="기업 이름 검색..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  disabled={firms.status !== 'success' || firmList.length === 0}
                />
              </div>

              <p className="form-hint" style={{ marginBottom: '0.75rem' }} aria-live="polite">
                {firms.status === 'success' &&
                  (query
                    ? `${filteredFirms.length}개 / 전체 ${firmList.length}개`
                    : `전체 ${firmList.length}개`)}
              </p>

              <div className="scroll-area">
                {firms.status === 'loading' && <LoadingState message="기업 목록을 불러오는 중..." />}
                {firms.status === 'error' && (
                  <ErrorState message={firms.error ?? ''} onRetry={firms.reload} />
                )}

                {firms.status === 'success' && filteredFirms.length === 0 && (
                  <EmptyState
                    title={query ? '검색 결과가 없습니다' : '해당 카테고리에 기업이 없습니다'}
                    hint={query ? '다른 검색어를 입력해 보세요.' : undefined}
                  />
                )}

                {firms.status === 'success' && filteredFirms.length > 0 && (
                  <ul className="firm-list" aria-label="기업 목록">
                    {filteredFirms.map((firm) => (
                      <li key={firm.path || firm.name}>
                        <button
                          type="button"
                          className="firm-item"
                          aria-current={selectedName === firm.name}
                          onClick={() => selectFirm(firm.name)}
                        >
                          <span className="firm-item-name">{firm.name}</span>
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
          {selectedFirm ? (
            <>
              <div className="header-row" style={{ marginBottom: '1rem' }}>
                <h3 className="section-title">{selectedFirm.name}</h3>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => setSelectedName(null)}
                >
                  <X size={16} aria-hidden="true" />
                  닫기
                </button>
              </div>
              <div className="scroll-area">
                {selectedFirm.summary?.trim() ? (
                  <Markdown content={selectedFirm.summary} />
                ) : (
                  <EmptyState
                    title="요약 내용이 없습니다"
                    hint="이 기업에는 아직 summary.md 파일이 없습니다."
                  />
                )}
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
