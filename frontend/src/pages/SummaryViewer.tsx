import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { ArrowUpRight, FileText, Search, X } from 'lucide-react';
import { getFirmDetail, getResultsSummary, getTaxonomy, searchFirms } from '../lib/data';
import { useAsync, type AsyncState } from '../lib/useAsync';
import { useMediaQuery } from '../lib/useMediaQuery';
import {
  parseResultsSummary,
  type FirmDetail,
  type FirmListItem,
  type FirmListResponse,
  type Taxonomy,
  type TaxonomyEntry,
} from '../lib/types';
import { categoryLabel, categoryTone, categoryViews } from '../lib/categories';
import { cx, formatCount, shortPlace } from '../lib/format';
import { splitSummary } from '../lib/summary';
import { ErrorState, LoadingState, Spinner } from '../components/States';
import Markdown from '../components/Markdown';
import Highlight from '../components/Highlight';
import { AiLine } from '../components/AiNotice';

/** How long typing must pause before the search reaches the URL and the API. */
const SEARCH_DEBOUNCE_MS = 250;

/** Offered when a search finds nothing. */
const EXAMPLE_QUERIES = ['반도체', 'LLM', '신약', '자율주행'];

const CONFIDENCE: Record<string, { label: string; steps: number }> = {
  high: { label: '높음', steps: 3 },
  medium: { label: '보통', steps: 2 },
  low: { label: '낮음', steps: 1 },
};

/** The open firm, addressed the way `GET /api/firms/:category/:name` expects. */
interface Selection {
  categoryId: string;
  name: string;
  address: string;
}

/** Taxonomy ids to their Korean names. */
interface Names {
  sectors: Map<string, string>;
  subsectors: Map<string, string>;
  verticals: Map<string, string>;
  businessModels: Map<string, string>;
  valueChain: Map<string, string>;
}

function buildNames(taxonomy: Taxonomy | null): Names {
  const byId = (entries?: TaxonomyEntry[]) => new Map((entries ?? []).map((e) => [e.id, e.name]));
  const subsectors = new Map<string, string>();
  for (const sector of taxonomy?.sectors ?? []) {
    for (const sub of sector.subsectors ?? []) subsectors.set(sub.id, sub.name);
  }
  return {
    sectors: byId(taxonomy?.sectors),
    subsectors,
    verticals: byId(taxonomy?.verticals),
    businessModels: byId(taxonomy?.business_models),
    valueChain: byId(taxonomy?.value_chain),
  };
}

/** "ICT·소프트웨어 › 데이터·AI 솔루션" */
function sectorLine(names: Names, sector: string | null, subsector: string | null): string {
  if (!sector) return '';
  const main = names.sectors.get(sector) ?? sector;
  return subsector ? `${main} › ${names.subsectors.get(subsector) ?? subsector}` : main;
}

function countBy(firms: FirmListItem[], keys: (firm: FirmListItem) => (string | null)[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const firm of firms) {
    for (const key of keys(firm)) {
      if (key) counts.set(key, (counts.get(key) ?? 0) + 1);
    }
  }
  return counts;
}

function Meter({ steps }: { steps: number }) {
  return (
    <span className="meter mr-2" aria-hidden="true">
      {[1, 2, 3].map((step) => (
        <i key={step} data-off={step > steps ? '' : undefined} />
      ))}
    </span>
  );
}

/** A firm's details on phones: rises from the bottom over the list, which keeps its place. */
function FirmSheet({
  open,
  onClose,
  labelledBy,
  children,
}: {
  open: boolean;
  onClose: () => void;
  labelledBy: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className="sheet"
      aria-labelledby={labelledBy}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        // A click on the dimmed area outside the sheet lands on the dialog itself.
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="flex justify-center pt-2.5 pb-1" aria-hidden="true">
        <span className="h-[5px] w-10 rounded-full bg-line" />
      </div>
      <button type="button" className="btn-icon absolute top-2.5 right-3" onClick={onClose} aria-label="닫기">
        <X size={20} strokeWidth={1.75} aria-hidden="true" />
      </button>
      <div className="scroll-area flex-1 px-5 pt-2 pb-[calc(1.5rem+env(safe-area-inset-bottom))]">{children}</div>
    </dialog>
  );
}

function FirmDetailView({
  selected,
  detail,
  names,
  term,
  headingId,
}: {
  selected: Selection;
  detail: AsyncState<FirmDetail | null>;
  names: Names;
  term: string;
  headingId: string;
}) {
  const data = detail.status === 'success' ? detail.data : null;
  const parts = useMemo(() => (data ? splitSummary(data.summary, data.name) : null), [data]);
  const seg = data?.segmentation ?? null;
  const place = shortPlace(data?.address || selected.address);
  const website = parts?.facts.find((fact) => fact.href);

  const facts: { label: string; value: ReactNode }[] = [];
  if (seg) {
    facts.push({ label: '섹터', value: sectorLine(names, seg.sector, seg.subsector) });
    const verticals = seg.verticals.filter((id) => id !== 'none');
    if (verticals.length) {
      facts.push({ label: '버티컬', value: verticals.map((id) => names.verticals.get(id) ?? id).join(' · ') });
    }
    if (seg.business_model) {
      facts.push({ label: '사업 모델', value: names.businessModels.get(seg.business_model) ?? seg.business_model });
    }
    if (seg.value_chain) {
      facts.push({ label: '가치사슬', value: names.valueChain.get(seg.value_chain) ?? seg.value_chain });
    }
    const confidence = CONFIDENCE[seg.confidence?.sector ?? ''];
    if (confidence) {
      facts.push({
        label: '분류 확신도',
        value: (
          <>
            <Meter steps={confidence.steps} />
            {confidence.label}
          </>
        ),
      });
    }
  }
  for (const fact of parts?.facts ?? []) {
    facts.push({
      label: fact.label,
      value: (
        <>
          {fact.href ? (
            <a className="link font-medium" href={fact.href} target="_blank" rel="noopener noreferrer">
              {fact.value}
            </a>
          ) : (
            fact.value
          )}
          {fact.note && <span className="ml-2 text-xs text-meta">{fact.note}</span>}
        </>
      ),
    });
  }

  const mapLink = `/firms?q=${encodeURIComponent(selected.name)}`;

  return (
    <article className="grid gap-5">
      <header className="grid gap-2.5">
        <div className="flex flex-wrap gap-1.5">
          <span className="pill">
            <span className="swatch" style={{ background: categoryTone(selected.categoryId) }} aria-hidden="true" />
            {categoryLabel(selected.categoryId, data?.category)}
          </span>
          {place && <span className="pill">{place}</span>}
        </div>
        <h2 id={headingId} className="text-[22px] leading-snug font-extrabold tracking-[-0.025em] md:text-2xl">
          {selected.name}
        </h2>
        <AiLine />
      </header>

      {detail.status === 'loading' && (
        <div className="grid gap-3" role="status">
          <span className="visually-hidden">요약을 불러오는 중입니다</span>
          {['100%', '92%', '96%', '60%'].map((width) => (
            <div key={width} className="skeleton h-4" style={{ width }} aria-hidden="true" />
          ))}
        </div>
      )}
      {detail.status === 'error' && <ErrorState message={detail.error ?? ''} onRetry={detail.reload} />}

      {data && (
        <>
          {facts.length > 0 && (
            <dl className="border-t border-line">
              {facts.map((fact) => (
                <div
                  key={fact.label}
                  className="grid grid-cols-[5.5rem_minmax(0,1fr)] gap-4 border-b border-line py-2.5 text-sm md:grid-cols-[6.5rem_minmax(0,1fr)]"
                >
                  <dt className="text-meta">{fact.label}</dt>
                  <dd className="font-medium [overflow-wrap:anywhere]">{fact.value}</dd>
                </div>
              ))}
            </dl>
          )}

          <div className="flex flex-wrap gap-2">
            {website?.href && (
              <a className="btn btn-primary" href={website.href} target="_blank" rel="noopener noreferrer">
                홈페이지 열기
                <ArrowUpRight size={16} strokeWidth={2} aria-hidden="true" />
              </a>
            )}
            <Link className={cx('btn', website?.href ? 'btn-secondary' : 'btn-primary')} to={mapLink}>
              지도에서 보기
            </Link>
          </div>

          {data.summary.trim() && parts ? (
            <div className="border-t border-line pt-5">
              <Markdown content={parts.body} highlight={term} />
            </div>
          ) : (
            <p className="rounded-xl bg-canvas px-4 py-3 text-sm text-meta">
              이 업체는 아직 요약이 없어요. summary.md 파일이 만들어지면 여기에 나와요.
            </p>
          )}
        </>
      )}
    </article>
  );
}

export default function SummaryViewer() {
  const location = useLocation();
  // Category, search and filters all live in the URL so a view is linkable
  // and the 개요 page can jump straight to a category or a search.
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
  // once typing pauses. A URL change from elsewhere (back/forward, a link from
  // 개요) rewrites the input.
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

  // Arriving from the search button or the "/" key puts the cursor here.
  const searchRef = useRef<HTMLInputElement>(null);
  const focusSearch = Boolean((location.state as { focusSearch?: boolean } | null)?.focusSearch);
  useEffect(() => {
    if (focusSearch) searchRef.current?.focus();
  }, [focusSearch, location.key]);

  const summary = useAsync(async () => parseResultsSummary(await getResultsSummary()));
  const categories = useMemo(() => categoryViews(summary.data?.categories ?? []), [summary.data]);

  const taxonomy = useAsync(getTaxonomy);
  const sectors = useMemo(() => taxonomy.data?.sectors ?? [], [taxonomy.data]);
  // "none" is never stored on a firm, so filtering by it could only come up empty.
  const verticals = useMemo(
    () => (taxonomy.data?.verticals ?? []).filter((v) => v.id !== 'none'),
    [taxonomy.data],
  );
  const names = useMemo(() => buildNames(taxonomy.data), [taxonomy.data]);

  // A stale bookmark can name an id that no longer exists; once the valid ids
  // are known, such a value is treated as unset.
  const category = summary.data ? (categories.some((c) => c.id === categoryParam) ? categoryParam : '') : categoryParam;
  const sector = taxonomy.data ? (sectors.some((s) => s.id === sectorParam) ? sectorParam : '') : sectorParam;
  const vertical = taxonomy.data
    ? verticals.some((v) => v.id === verticalParam)
      ? verticalParam
      : ''
    : verticalParam;
  const searchTerm = qParam.trim();
  const filtering = Boolean(searchTerm || sector || vertical || segmentedOnly);

  // Only the search term goes to the server. Category and segmentation are
  // narrowed here, so every chip and option can say how many firms it leaves.
  const firms = useAsync(() => searchFirms({ q: searchTerm || undefined }), [searchTerm]);

  // Keep the previous result on screen while a refined search loads, rather
  // than flashing a spinner on every pause in typing.
  const [shownFirms, setShownFirms] = useState<FirmListResponse | null>(null);
  if (firms.data && firms.data !== shownFirms) {
    setShownFirms(firms.data);
  }
  const base = firms.status === 'error' ? null : (firms.data ?? shownFirms);
  const refreshing = firms.status === 'loading' && base !== null;

  const all = base?.firms ?? [];
  const keepSegmented = (f: FirmListItem) => !segmentedOnly || f.segmented;
  const keepCategory = (f: FirmListItem) => !category || f.category_id === category;
  const keepSector = (f: FirmListItem) => !sector || f.sector === sector;
  const keepVertical = (f: FirmListItem) => !vertical || f.verticals.includes(vertical);

  const visible = all.filter((f) => keepSegmented(f) && keepCategory(f) && keepSector(f) && keepVertical(f));
  const categoryCounts = countBy(
    all.filter((f) => keepSegmented(f) && keepSector(f) && keepVertical(f)),
    (f) => [f.category_id],
  );
  const sectorCounts = countBy(
    all.filter((f) => keepSegmented(f) && keepCategory(f) && keepVertical(f)),
    (f) => [f.sector],
  );
  const verticalCounts = countBy(
    all.filter((f) => keepSegmented(f) && keepCategory(f) && keepSector(f)),
    (f) => f.verticals,
  );
  // Before the first result arrives, the chips show the category totals.
  const chipCount = (id: string | null) =>
    base
      ? id
        ? (categoryCounts.get(id) ?? 0)
        : [...categoryCounts.values()].reduce((a, b) => a + b, 0)
      : id
        ? (categories.find((c) => c.id === id)?.count ?? 0)
        : (summary.data?.total ?? 0);
  // Sector and vertical filters only help once some firms are segmented.
  const showSegmentFilters =
    taxonomy.status === 'success' && (all.some((f) => f.segmented) || Boolean(sector || vertical || segmentedOnly));

  const [selected, setSelected] = useState<Selection | null>(null);
  // Full summaries are fetched one at a time, only for the firm being read.
  const detail = useAsync(async () => {
    if (!selected) return null;
    return getFirmDetail(selected.categoryId, selected.name);
  }, [selected?.categoryId, selected?.name]);

  const isDesktop = useMediaQuery('(min-width: 1024px)');

  const resetFilters = () => {
    setDraft('');
    updateParams({ q: '', sector: '', vertical: '', segmented: '', category: '' });
  };

  const runExample = (query: string) => {
    setDraft(query);
    updateParams({ q: query, sector: '', vertical: '', segmented: '', category: '' });
  };

  const statusText = !base
    ? ''
    : filtering || category
      ? `${formatCount(visible.length)}곳 · 전체 ${formatCount(base.total)}곳 중`
      : `전체 ${formatCount(visible.length)}곳`;

  const detailView = selected && (
    <FirmDetailView
      selected={selected}
      detail={detail}
      names={names}
      term={searchTerm}
      headingId="firm-detail-heading"
    />
  );

  return (
    <div className="flex flex-col gap-4 lg:h-full">
      <header className="page-header mb-0">
        <h1 className="page-title">업체 요약</h1>
        <p className="page-subtitle">업체 이름이나 키워드로 찾고, AI가 정리한 요약을 읽어요</p>
      </header>

      <div className="grid gap-4 lg:min-h-0 lg:flex-1 lg:grid-cols-[minmax(340px,400px)_minmax(0,1fr)] lg:grid-rows-[minmax(0,1fr)]">
        <section aria-label="업체 목록" className="card flex flex-col p-0 md:p-0 lg:min-h-0">
          {/* On phones the search stays pinned under the top bar while the list scrolls. */}
          <div className="sticky top-14 z-10 rounded-t-card bg-card px-4 pt-4 pb-3 lg:static">
            <div className="flex h-11 items-center gap-2 rounded-xl bg-canvas pr-1.5 pl-3 focus-within:outline-2 focus-within:outline-pen">
              <Search size={17} strokeWidth={1.75} className="flex-none text-meta" aria-hidden="true" />
              <label className="visually-hidden" htmlFor="firm-search">
                업체 이름이나 요약 내용으로 찾기
              </label>
              <input
                ref={searchRef}
                id="firm-search"
                type="search"
                enterKeyHint="search"
                autoComplete="off"
                placeholder="업체 이름이나 키워드"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                className="h-full min-w-0 flex-1 bg-transparent text-[15px] font-semibold placeholder:font-normal placeholder:text-meta focus-visible:outline-none [&::-webkit-search-cancel-button]:hidden"
              />
              {draft ? (
                <button
                  type="button"
                  className="grid size-8 flex-none place-items-center rounded-full"
                  onClick={() => {
                    setDraft('');
                    updateParams({ q: '' });
                    searchRef.current?.focus();
                  }}
                  aria-label="검색어 지우기"
                >
                  <span className="grid size-[18px] place-items-center rounded-full bg-faint text-card">
                    <X size={11} strokeWidth={3} aria-hidden="true" />
                  </span>
                </button>
              ) : (
                <kbd className="kbd mr-1 hidden lg:inline-block" aria-hidden="true">
                  /
                </kbd>
              )}
            </div>
          </div>

          <div className="grid gap-3 border-b border-line px-4 pb-3">
            {summary.status === 'error' && (
              <p className="text-sm text-meta">분야 목록을 불러오지 못했어요. {summary.error}</p>
            )}
            {categories.length > 0 && (
              <div
                role="group"
                aria-label="분야"
                className="-mx-4 flex gap-1.5 overflow-x-auto px-4 [scrollbar-width:none] lg:mx-0 lg:flex-wrap lg:overflow-visible lg:px-0"
              >
                <button
                  type="button"
                  className="chip"
                  aria-pressed={!category}
                  onClick={() => updateParams({ category: '' })}
                >
                  전체
                  <span className="chip-count">{formatCount(chipCount(null))}</span>
                </button>
                {categories.map((cat) => {
                  const count = chipCount(cat.id);
                  return (
                    <button
                      key={cat.id}
                      type="button"
                      className="chip"
                      aria-pressed={category === cat.id}
                      data-empty={count === 0}
                      onClick={() => updateParams({ category: cat.id })}
                    >
                      <span className="swatch" style={{ background: cat.tone }} aria-hidden="true" />
                      {cat.label}
                      <span className="chip-count">{formatCount(count)}</span>
                    </button>
                  );
                })}
              </div>
            )}

            {showSegmentFilters && (
              <div role="group" aria-label="세분류 필터" className="flex flex-wrap items-center gap-1.5">
                <label className="visually-hidden" htmlFor="filter-sector">
                  산업 섹터
                </label>
                <select
                  id="filter-sector"
                  className="select-chip"
                  data-active={Boolean(sector)}
                  value={sector}
                  onChange={(event) => updateParams({ sector: event.target.value })}
                >
                  <option value="">섹터 전체</option>
                  {sectors.map((s) => {
                    const count = sectorCounts.get(s.id) ?? 0;
                    return (
                      <option key={s.id} value={s.id} disabled={count === 0 && s.id !== sector}>
                        {s.name} ({count})
                      </option>
                    );
                  })}
                </select>

                <label className="visually-hidden" htmlFor="filter-vertical">
                  기술 버티컬
                </label>
                <select
                  id="filter-vertical"
                  className="select-chip"
                  data-active={Boolean(vertical)}
                  value={vertical}
                  onChange={(event) => updateParams({ vertical: event.target.value })}
                >
                  <option value="">버티컬 전체</option>
                  {verticals.map((v) => {
                    const count = verticalCounts.get(v.id) ?? 0;
                    return (
                      <option key={v.id} value={v.id} disabled={count === 0 && v.id !== vertical}>
                        {v.name} ({count})
                      </option>
                    );
                  })}
                </select>

                <button
                  type="button"
                  className="chip"
                  aria-pressed={segmentedOnly}
                  onClick={() => updateParams({ segmented: segmentedOnly ? '' : 'true' })}
                >
                  세분류된 업체만
                </button>
              </div>
            )}
            {taxonomy.status === 'error' && (
              <p className="text-[13px] text-meta">세분류 목록을 불러오지 못해 섹터·버티컬 필터를 쓸 수 없어요.</p>
            )}

            <div className="flex min-h-5 items-center gap-2" aria-live="polite">
              <span className="caption">{statusText}</span>
              {refreshing && <Spinner small label="찾는 중" />}
              {(filtering || category) && (
                <button
                  type="button"
                  className="ml-auto text-[13px] font-semibold text-ink-2 hover:text-ink"
                  onClick={resetFilters}
                >
                  필터 모두 지우기
                </button>
              )}
            </div>
          </div>

          <div className="scroll-area px-2 py-2 lg:flex-1">
            {firms.status === 'loading' && !base && <LoadingState message="업체 목록을 불러오는 중..." />}
            {firms.status === 'error' && <ErrorState message={firms.error ?? ''} onRetry={firms.reload} />}

            {base && visible.length === 0 && (
              <div className="grid justify-items-center gap-3 px-4 py-10 text-center">
                <p className="font-bold">
                  {searchTerm ? `'${searchTerm}' 검색 결과가 없어요` : '조건에 맞는 업체가 없어요'}
                </p>
                <p className="text-sm text-meta">이렇게 찾아보세요</p>
                <div className="flex flex-wrap justify-center gap-1.5">
                  {EXAMPLE_QUERIES.filter((q) => q !== searchTerm).map((query) => (
                    <button key={query} type="button" className="chip" onClick={() => runExample(query)}>
                      {query}
                    </button>
                  ))}
                </div>
                {(filtering || category) && (
                  <button type="button" className="link text-[13.5px]" onClick={resetFilters}>
                    필터 모두 지우기
                  </button>
                )}
              </div>
            )}

            {visible.length > 0 && (
              <ul aria-label="검색 결과" aria-busy={refreshing} className="grid gap-0.5">
                {visible.map((firm) => {
                  const current = selected?.categoryId === firm.category_id && selected?.name === firm.name;
                  const meta = [
                    !category && categoryLabel(firm.category_id, firm.category),
                    sectorLine(names, firm.sector, firm.subsector),
                    shortPlace(firm.address),
                  ]
                    .filter(Boolean)
                    .join(' · ');
                  return (
                    <li key={`${firm.category_id}/${firm.name}`}>
                      <button
                        type="button"
                        aria-current={current}
                        onClick={() =>
                          setSelected({ categoryId: firm.category_id, name: firm.name, address: firm.address })
                        }
                        className={cx(
                          'grid w-full gap-0.5 rounded-xl px-3 py-2.5 text-left transition-colors',
                          current ? 'bg-pen-tint' : 'hover:bg-canvas',
                        )}
                      >
                        <span className={cx('truncate text-[14.5px] leading-snug font-bold', current && 'text-pen')}>
                          <Highlight text={firm.name} term={searchTerm} />
                        </span>
                        <span className="flex min-w-0 items-center gap-1.5 text-xs text-meta">
                          <span
                            className="swatch size-2"
                            style={{ background: categoryTone(firm.category_id) }}
                            aria-hidden="true"
                          />
                          <span className="truncate">{meta}</span>
                        </span>
                        {firm.snippet && (
                          <span className="line-clamp-2 text-[13px] leading-normal text-ink-2">
                            <Highlight text={firm.snippet} term={searchTerm} />
                          </span>
                        )}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </section>

        {isDesktop && (
          <section aria-label="업체 요약" className="card scroll-area px-8 py-7 lg:min-h-0">
            {detailView ?? (
              <div className="grid h-full place-content-center justify-items-center gap-2 p-8 text-center">
                <FileText size={28} strokeWidth={1.5} className="mb-1 text-faint" aria-hidden="true" />
                <p className="font-bold">업체를 고르면 요약이 여기에 나와요</p>
                <p className="max-w-xs text-sm text-meta">
                  검색어는 목록과 요약 안에서 형광펜으로 표시돼요.
                </p>
              </div>
            )}
          </section>
        )}
      </div>

      {!isDesktop && (
        <FirmSheet open={selected !== null} onClose={() => setSelected(null)} labelledBy="firm-detail-heading">
          {detailView}
        </FirmSheet>
      )}
    </div>
  );
}
