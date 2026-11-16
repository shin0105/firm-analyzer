import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight, Download, Play, RotateCw } from 'lucide-react';
import { STATIC_SITE } from '../lib/api';
import { exportCsvUrl, getResultsSummary } from '../lib/data';
import { useAsync } from '../lib/useAsync';
import { parseResultsSummary } from '../lib/types';
import { categoryViews, type CategoryView } from '../lib/categories';
import { getRosterRegions, type RegionCount } from '../lib/roster';
import { cx, formatCount, formatShare, niceAxis } from '../lib/format';
import { EmptyState, ErrorState } from '../components/States';

/** Searches that find firms in the current data; each opens 업체 요약. */
const EXAMPLE_QUERIES = ['반도체', 'LLM', '신약', '자율주행', '로보틱스'];

/** Regions shown as their own bar; the rest share one. */
const REGION_ROWS = 7;

function Skeleton({ className, width }: { className: string; width?: string }) {
  return <div className={cx('skeleton', className)} style={width ? { width } : undefined} aria-hidden="true" />;
}

/** One bar for the whole: the specialised categories next to how big 일반 is. */
function ProportionBar({ categories, total }: { categories: CategoryView[]; total: number }) {
  const shown = categories.filter((category) => category.count > 0);
  return (
    <div
      role="img"
      aria-label={shown.map((c) => `${c.label} ${formatShare(c.count, total)}`).join(', ')}
      className="flex h-[26px] gap-0.5 overflow-hidden rounded-md"
    >
      {shown.map((category) => (
        <span
          key={category.id}
          className="block h-full"
          style={{ width: `${(category.count / total) * 100}%`, background: category.tone }}
        />
      ))}
    </div>
  );
}

function TotalCard({ categories, total }: { categories: CategoryView[]; total: number }) {
  return (
    <section
      aria-labelledby="total-heading"
      className="card grid gap-6 md:grid-cols-[auto_minmax(0,1fr)] md:items-end md:gap-12 md:px-7 md:py-6"
    >
      <div>
        <h2 id="total-heading" className="text-sm font-medium text-ink-2">
          AI가 요약한 업체
        </h2>
        <p className="mt-0.5 text-[44px] leading-[1.1] font-extrabold tracking-[-0.035em] tabular-nums">
          {formatCount(total)}
          <span className="ml-1 text-[22px] font-bold tracking-normal text-ink-2">곳</span>
        </p>
        <p className="caption mt-1.5">{categories.length}개 분야 · 공개 웹 검색 + AI 요약</p>
      </div>
      <figure>
        <ProportionBar categories={categories} total={total} />
        <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-[13px] text-ink-2">
          {categories.map((category) => (
            <li key={category.id} className="inline-flex items-center gap-1.5">
              <span className="swatch" style={{ background: category.tone }} aria-hidden="true" />
              {category.label}
              <b className="font-mono text-xs font-medium text-ink">{formatShare(category.count, total)}</b>
            </li>
          ))}
        </ul>
        <figcaption className="caption mt-2.5">
          <b>그림 1.</b> 분야별 비율 · n = {formatCount(total)}
        </figcaption>
      </figure>
    </section>
  );
}

function CategoryCard({ categories, total }: { categories: CategoryView[]; total: number }) {
  return (
    <section aria-labelledby="category-heading" className="card">
      <div className="mb-1 flex items-baseline justify-between gap-3">
        <h2 id="category-heading" className="section-title">
          분야별
        </h2>
        <span className="caption">누르면 목록으로</span>
      </div>
      <ul>
        {categories.map((category) => (
          <li key={category.id} className="border-t border-line first:border-t-0">
            <Link
              to={`/summary?category=${encodeURIComponent(category.id)}`}
              className="group -mx-2 grid grid-cols-[0.625rem_minmax(0,1fr)_auto_3.25rem_1rem] items-center gap-3 rounded-xl px-2 py-3 hover:bg-canvas"
            >
              <span className="swatch" style={{ background: category.tone }} aria-hidden="true" />
              <span className="min-w-0">
                <span className="block text-[15px] font-medium">{category.label}</span>
                {category.note && <span className="block text-xs text-meta">{category.note}</span>}
              </span>
              <span className="text-[15px] font-bold tabular-nums">
                {formatCount(category.count)}
                <span className="visually-hidden">곳</span>
              </span>
              <span className="text-right font-mono text-xs text-meta">{formatShare(category.count, total)}</span>
              <ChevronRight
                size={16}
                strokeWidth={1.75}
                className="text-faint group-hover:text-ink-2"
                aria-hidden="true"
              />
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

function ExamplesCard() {
  return (
    <section aria-labelledby="examples-heading" className="card">
      <h2 id="examples-heading" className="section-title">
        이렇게 찾아보세요
      </h2>
      <p className="mb-3 text-[13px] text-meta">업체 이름과 AI 요약 전체에서 찾아요. 어느 페이지에서든 / 키로 검색할 수 있어요.</p>
      <div className="flex flex-wrap gap-1.5">
        {EXAMPLE_QUERIES.map((query) => (
          <Link key={query} className="chip" to={`/summary?q=${encodeURIComponent(query)}`}>
            {query}
          </Link>
        ))}
      </div>
    </section>
  );
}

function RegionChart({ regions }: { regions: RegionCount[] }) {
  const top = regions.length > REGION_ROWS + 1 ? regions.slice(0, REGION_ROWS) : regions;
  const rest = regions.slice(top.length);
  const restCount = rest.reduce((sum, region) => sum + region.count, 0);
  const { domain, ticks } = niceAxis(Math.max(...regions.map((region) => region.count), restCount));
  const width = (count: number) => `${(count / domain) * 100}%`;
  // The label and value columns, shared by the rows and the axis below them.
  const columns = 'grid grid-cols-[4.75rem_minmax(0,1fr)_2.25rem] items-center gap-2.5';

  return (
    <figure>
      <ul className="grid gap-1">
        {top.map((region) => (
          <li key={region.id}>
            <Link
              to={`/firms?region=${encodeURIComponent(region.id)}`}
              className={cx(columns, 'group -mx-1.5 rounded-lg px-1.5 py-1 text-[13px] hover:bg-canvas')}
            >
              <span className="truncate">{region.label}</span>
              <span className="relative h-3">
                <span
                  className="absolute inset-y-0 left-0 rounded-r-[3px] bg-ink-2 group-hover:bg-pen"
                  style={{ width: width(region.count) }}
                />
              </span>
              <span className="text-right font-mono text-xs tabular-nums">{formatCount(region.count)}</span>
            </Link>
          </li>
        ))}
        {rest.length > 0 && (
          <li className={cx(columns, 'px-0 py-1 text-[13px] text-meta')} title={rest.map((r) => r.label).join(', ')}>
            <span className="truncate">그 외 {rest.length}개 청</span>
            <span className="relative h-3">
              <span className="absolute inset-y-0 left-0 rounded-r-[3px] bg-line" style={{ width: width(restCount) }} />
            </span>
            <span className="text-right font-mono text-xs text-ink tabular-nums">{formatCount(restCount)}</span>
          </li>
        )}
      </ul>
      <div className={cx(columns, 'mt-1.5')} aria-hidden="true">
        <span />
        <span className="relative h-5 border-t border-ink">
          {ticks.map((tick) => (
            <span
              key={tick}
              className="absolute top-1 -translate-x-1/2 font-mono text-[10.5px] text-meta tabular-nums before:absolute before:-top-1 before:left-1/2 before:h-1 before:w-px before:bg-ink"
              style={{ left: width(tick) }}
            >
              {formatCount(tick)}
            </span>
          ))}
        </span>
        <span />
      </div>
    </figure>
  );
}

function RegionCard() {
  const roster = useAsync(getRosterRegions);
  return (
    <section aria-labelledby="region-heading" className="card">
      <div className="mb-3 flex items-baseline justify-between gap-3">
        <h2 id="region-heading" className="section-title">
          관할 병무청별 배정 명단
        </h2>
        {roster.data && (
          <span className="caption whitespace-nowrap">
            {roster.data.year ? `${roster.data.year} · ` : ''}
            {formatCount(roster.data.total)}곳
          </span>
        )}
      </div>

      {roster.status === 'loading' && (
        <div className="grid gap-3" role="status" aria-label="배정 명단을 불러오는 중">
          {[96, 52, 22, 14, 10, 8, 7].map((w) => (
            <Skeleton key={w} className="h-3" width={`${w}%`} />
          ))}
        </div>
      )}
      {roster.status === 'error' && (
        <div className="grid justify-items-start gap-2 py-4 text-sm text-meta">
          <p>배정 명단을 불러오지 못했어요. {roster.error}</p>
          <button type="button" className="btn btn-secondary btn-sm" onClick={roster.reload}>
            <RotateCw size={15} aria-hidden="true" />
            다시 시도
          </button>
        </div>
      )}
      {roster.data && roster.data.regions.length > 0 && (
        <>
          <RegionChart regions={roster.data.regions} />
          <p className="caption mt-2">
            <b>그림 2.</b> 관할 지방병무청별 업체 수 · 병무청 인원배정 현황
          </p>
          <Link className="link mt-4 inline-block text-[13.5px]" to="/firms">
            배정 지도에서 보기
          </Link>
        </>
      )}
    </section>
  );
}

export default function Dashboard() {
  const summary = useAsync(async () => parseResultsSummary(await getResultsSummary()));
  const categories = useMemo(() => categoryViews(summary.data?.categories ?? []), [summary.data]);
  const total = summary.data?.total ?? 0;

  return (
    <div className="grid gap-4">
      <div className="header-row mb-1">
        <div className="page-header">
          <h1 className="page-title">개요</h1>
          <p className="page-subtitle">AI가 요약한 업체와 병무청 인원배정 명단을 한눈에 봐요</p>
        </div>
        <div className="button-row">
          {/* Every firm with its summary fields: rebuilt by Flask, or the snapshot's copy. */}
          <a className="btn btn-secondary btn-sm" href={exportCsvUrl} download>
            <Download size={15} strokeWidth={1.75} aria-hidden="true" />
            CSV 내려받기
          </a>
          {/* The static site's data only changes with a new deploy. */}
          {!STATIC_SITE && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={summary.reload}
              disabled={summary.status === 'loading'}
            >
              <RotateCw size={15} strokeWidth={1.75} aria-hidden="true" />
              새로고침
            </button>
          )}
        </div>
      </div>

      {summary.status === 'error' && (
        <div className="card">
          <ErrorState message={summary.error ?? ''} onRetry={summary.reload} />
        </div>
      )}

      {summary.status === 'loading' && (
        <div className="card grid gap-3 md:grid-cols-[12rem_minmax(0,1fr)] md:items-end md:gap-12" role="status">
          <span className="visually-hidden">개요를 불러오는 중입니다</span>
          <div className="grid gap-2">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-11 w-40" />
          </div>
          <Skeleton className="h-[26px]" />
        </div>
      )}

      {summary.status === 'success' && categories.length === 0 && (
        <div className="card">
          <EmptyState title="아직 요약한 업체가 없어요" hint="필터와 검색·요약을 먼저 실행해 주세요." />
          {!STATIC_SITE && (
            <div className="flex justify-center">
              <Link className="btn btn-primary btn-sm" to="/pipeline">
                <Play size={15} aria-hidden="true" />
                파이프라인 실행으로 이동
              </Link>
            </div>
          )}
        </div>
      )}

      {summary.status === 'success' && categories.length > 0 && <TotalCard categories={categories} total={total} />}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.12fr)_minmax(0,1fr)] lg:items-start">
        <div className="grid gap-4">
          {summary.status === 'success' && categories.length > 0 && (
            <CategoryCard categories={categories} total={total} />
          )}
          <ExamplesCard />
        </div>
        <RegionCard />
      </div>
    </div>
  );
}
