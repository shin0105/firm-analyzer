import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { Filter, Layers, Play, RotateCw, Search, Square, Workflow } from 'lucide-react';
import { api, errorMessage } from '../lib/api';
import { useAsync } from '../lib/useAsync';
import type {
  Job,
  JobKind,
  JobStatus,
  JobWithLog,
  JobsResponse,
  ProvidersResponse,
} from '../lib/types';
import { EmptyState, ErrorState, LoadingState, Spinner } from '../components/States';

/** Poll interval while a job runs; the scripts print a line per firm. */
const POLL_MS = 1000;
/** Lines kept in the browser; the server keeps its own bounded tail. */
const MAX_CLIENT_LOG_LINES = 5000;

const KIND_LABELS: Record<JobKind, string> = {
  filter: '필터',
  summarize: '검색·요약',
  segment: '세분류 백필',
  pipeline: '필터 → 검색·요약',
};

const STATUS_LABELS: Record<JobStatus, string> = {
  queued: '대기 중',
  running: '실행 중',
  succeeded: '완료',
  failed: '실패',
  cancelled: '취소됨',
};

function isActive(status: JobStatus | undefined): boolean {
  return status === 'queued' || status === 'running';
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return '—';
  const total = Math.max(0, Math.round(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h) return `${h}시간 ${m}분`;
  if (m) return `${m}분 ${String(s).padStart(2, '0')}초`;
  return `${s}초`;
}

function formatTime(epochSeconds: number): string {
  return new Date(epochSeconds * 1000).toLocaleString('ko-KR', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** An optional positive integer field: empty means "no limit". */
function parseLimit(value: string): number | undefined {
  const trimmed = value.trim();
  return trimmed ? Number(trimmed) : undefined;
}

interface Feed {
  jobId: string;
  job: JobWithLog | null;
  lines: string[];
  /** Earlier lines were dropped, by the server's buffer or the client cap. */
  truncated: boolean;
  error: string | null;
}

/**
 * Follows one job: polls `GET /api/jobs/:id?since=n` while it runs, appending
 * only the new log lines, and calls `onFinish` once it settles.
 *
 * State is written only from the poll callbacks, and a feed recorded for a
 * different job id is never returned, so switching jobs cannot show stale lines.
 */
function useJobFeed(jobId: string | null, onFinish: (jobId: string) => void): Feed | null {
  const [feed, setFeed] = useState<Feed | null>(null);
  const onFinishRef = useRef(onFinish);
  useEffect(() => {
    onFinishRef.current = onFinish;
  });

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    let timer: number | undefined;
    let next = 0;
    let lines: string[] = [];
    let truncated = false;
    let lastJob: JobWithLog | null = null;

    const poll = async () => {
      try {
        const res = await api.get<JobWithLog>(`/api/jobs/${encodeURIComponent(jobId)}`, {
          params: { since: next },
        });
        if (cancelled) return;
        const job = res.data;
        lastJob = job;
        truncated ||= job.log_truncated;
        lines = lines.concat(job.log);
        if (lines.length > MAX_CLIENT_LOG_LINES) {
          lines = lines.slice(-MAX_CLIENT_LOG_LINES);
          truncated = true;
        }
        next = job.log_next;
        setFeed({ jobId, job, lines, truncated, error: null });

        if (isActive(job.status)) {
          timer = window.setTimeout(poll, POLL_MS);
        } else {
          onFinishRef.current(jobId);
        }
      } catch (err) {
        if (cancelled) return;
        // A 404 means the server restarted and forgot the job: stop polling.
        const gone = axios.isAxiosError(err) && err.response?.status === 404;
        setFeed({
          jobId,
          job: lastJob,
          lines,
          truncated,
          error: gone ? '서버가 이 작업을 더 이상 기억하지 않습니다 (서버 재시작).' : errorMessage(err),
        });
        if (!gone) timer = window.setTimeout(poll, POLL_MS * 3);
      }
    };

    void poll();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [jobId]);

  return feed?.jobId === jobId ? feed : null;
}

function StatusBadge({ status }: { status: JobStatus }) {
  return (
    <span className="status-badge" data-status={status}>
      {isActive(status) && <Spinner small />}
      {STATUS_LABELS[status]}
    </span>
  );
}

function JobProgress({ job }: { job: Job }) {
  const { progress } = job;
  const stepText =
    job.steps.length > 1 ? `${job.step_index + 1}/${job.steps.length}단계 · ${job.steps[job.step_index]}` : null;

  if (!progress || progress.total === 0) {
    return stepText ? <p className="form-hint">{stepText}</p> : null;
  }
  const percent = Math.round((progress.current / progress.total) * 100);
  return (
    <div className="job-progress">
      <div className="job-progress-text">
        <span>{stepText ?? '진행률'}</span>
        <span>
          {progress.current.toLocaleString('ko-KR')} / {progress.total.toLocaleString('ko-KR')} ({percent}%)
        </span>
      </div>
      <span
        className="stat-bar"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={progress.total}
        aria-valuenow={progress.current}
        aria-label="작업 진행률"
      >
        <span
          className="stat-bar-fill"
          style={{ width: `${percent}%`, background: 'var(--color-pen)' }}
        />
      </span>
    </div>
  );
}

function JobLog({ lines, truncated }: { lines: string[]; truncated: boolean }) {
  const ref = useRef<HTMLPreElement>(null);
  // Follow new output unless the reader has scrolled up to look at something.
  const stickToBottom = useRef(true);

  useEffect(() => {
    const el = ref.current;
    if (el && stickToBottom.current) el.scrollTop = el.scrollHeight;
  }, [lines]);

  return (
    <pre
      ref={ref}
      className="job-log"
      tabIndex={0}
      aria-label="작업 로그"
      onScroll={(e) => {
        const el = e.currentTarget;
        stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 24;
      }}
    >
      {truncated && <span className="text-muted">… 이전 로그는 생략되었습니다{'\n'}</span>}
      {lines.length ? lines.join('\n') : <span className="text-muted">출력을 기다리는 중...</span>}
    </pre>
  );
}

export default function Pipeline() {
  const jobsList = useAsync(async () => (await api.get<JobsResponse>('/api/jobs')).data);
  const providers = useAsync(async () => (await api.get<ProvidersResponse>('/api/llm/providers')).data);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [provider, setProvider] = useState('');
  const [summarize, setSummarize] = useState({ dry_run: true, limit: '5', no_segmentation: false });
  const [segment, setSegment] = useState({ dry_run: true, limit: '', relocate: false, force: false });
  const [starting, setStarting] = useState<JobKind | null>(null);
  const [startError, setStartError] = useState<string | null>(null);

  // Show what the user picked, else whatever is running, else the latest run.
  const shownId = selectedId ?? jobsList.data?.active ?? jobsList.data?.jobs[0]?.id ?? null;
  // Once a job settles, pin it so the panel keeps showing it while the job
  // list reloads, rather than briefly falling back to another job.
  const feed = useJobFeed(shownId, (finishedId) => {
    setSelectedId(finishedId);
    jobsList.reload();
  });
  const shownJob = feed?.job ?? null;

  const busy =
    starting !== null || Boolean(jobsList.data?.active) || isActive(shownJob?.status);

  const providerList = providers.data?.providers ?? [];
  const activeProvider = providerList.find((p) => p.id === providers.data?.active);
  const chosenProvider = providerList.find((p) => p.id === provider);
  const providerMissingKey = (chosenProvider ?? activeProvider)?.configured === false;

  const start = async (kind: JobKind, options: Record<string, unknown>) => {
    setStarting(kind);
    setStartError(null);
    try {
      const res = await api.post<JobWithLog>('/api/jobs', { kind, options });
      setSelectedId(res.data.id);
      jobsList.reload();
    } catch (err) {
      setStartError(errorMessage(err));
      // Already running: switch the panel to the job that is.
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        const active = (err.response.data as { active?: string } | undefined)?.active;
        if (active) setSelectedId(active);
        jobsList.reload();
      }
    } finally {
      setStarting(null);
    }
  };

  const cancel = async (jobId: string) => {
    try {
      await api.post(`/api/jobs/${encodeURIComponent(jobId)}/cancel`);
    } catch (err) {
      setStartError(errorMessage(err));
    }
  };

  const withProvider = (options: Record<string, unknown>) =>
    provider ? { ...options, provider } : options;

  const summarizeOptions = () =>
    withProvider({
      dry_run: summarize.dry_run,
      no_segmentation: summarize.no_segmentation,
      ...(parseLimit(summarize.limit) !== undefined && { limit: parseLimit(summarize.limit) }),
    });

  const startButton = (kind: JobKind, label: string, options: () => Record<string, unknown>, primary = true) => (
    <button
      type="button"
      className={`btn ${primary ? 'btn-primary' : 'btn-secondary'} btn-sm`}
      onClick={() => void start(kind, options())}
      disabled={busy}
    >
      {starting === kind ? <Spinner small label="시작 중" /> : <Play size={16} aria-hidden="true" />}
      {label}
    </button>
  );

  return (
    <div>
      <div className="header-row">
        <div className="page-header">
          <h2 className="page-title">파이프라인 실행</h2>
          <p className="page-subtitle">
            필터·검색 요약·세분류 작업을 백그라운드로 실행하고 진행 상황을 확인합니다
          </p>
        </div>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={jobsList.reload}
          disabled={jobsList.status === 'loading'}
        >
          <RotateCw size={16} aria-hidden="true" />
          새로고침
        </button>
      </div>

      <div className="form-group pipeline-provider">
        <label className="form-label" htmlFor="pipeline-provider">
          요약·세분류에 사용할 AI
        </label>
        <select
          id="pipeline-provider"
          className="form-input"
          value={provider}
          onChange={(e) => setProvider(e.target.value)}
          disabled={providers.status !== 'success'}
        >
          <option value="">
            config.yml 기본값{activeProvider ? ` (${activeProvider.label} · ${activeProvider.model})` : ''}
          </option>
          {providerList.map((p) => (
            <option key={p.id} value={p.id} disabled={!p.configured}>
              {p.label} ({p.model}){p.configured ? '' : ' — API 키 없음'}
            </option>
          ))}
        </select>
        {providerMissingKey && (
          <p className="form-hint" role="alert">
            선택한 AI의 API 키가 서버에 없습니다. 드라이런만 실행할 수 있습니다.
          </p>
        )}
      </div>

      <div aria-live="polite">
        {startError && (
          <div className="alert alert-error" style={{ marginBottom: '1rem' }}>
            <div className="alert-body">{startError}</div>
          </div>
        )}
      </div>

      <div className="pipeline-grid">
        <section className="glass-card card-tight pipeline-task" aria-labelledby="task-filter">
          <h3 className="section-title" id="task-filter">
            <Filter size={18} aria-hidden="true" /> 필터
          </h3>
          <p className="form-hint">
            config.yml의 위치 필터로 원본 목록을 걸러 <code>data/filtered_firms.csv</code>를 만듭니다.
            API 호출이 없습니다.
          </p>
          <div className="button-row pipeline-actions">
            {startButton('filter', '필터 실행', () => ({}))}
          </div>
        </section>

        <section className="glass-card card-tight pipeline-task" aria-labelledby="task-summarize">
          <h3 className="section-title" id="task-summarize">
            <Search size={18} aria-hidden="true" /> 검색·요약
          </h3>
          <p className="form-hint">
            필터된 기업을 웹에서 검색하고 AI로 요약·분류합니다. 이미 처리한 기업은 건너뜁니다.
          </p>
          <div className="form-group">
            <label className="form-label" htmlFor="summarize-limit">
              처리할 기업 수 (비우면 전체)
            </label>
            <input
              id="summarize-limit"
              className="form-input"
              type="number"
              min={1}
              inputMode="numeric"
              value={summarize.limit}
              onChange={(e) => setSummarize({ ...summarize, limit: e.target.value })}
            />
          </div>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={summarize.dry_run}
              onChange={(e) => setSummarize({ ...summarize, dry_run: e.target.checked })}
            />
            <span>드라이런 (검색어만 확인, API 호출 없음)</span>
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={summarize.no_segmentation}
              onChange={(e) => setSummarize({ ...summarize, no_segmentation: e.target.checked })}
            />
            <span>세분류 없이 요약만</span>
          </label>
          <div className="button-row pipeline-actions">
            {startButton('summarize', '요약 실행', summarizeOptions)}
            {startButton('pipeline', '필터 후 요약', summarizeOptions, false)}
          </div>
        </section>

        <section className="glass-card card-tight pipeline-task" aria-labelledby="task-segment">
          <h3 className="section-title" id="task-segment">
            <Layers size={18} aria-hidden="true" /> 세분류 백필
          </h3>
          <p className="form-hint">
            세분류가 없는 기업을 저장된 검색 결과로 분류합니다. 새 검색 없이 기업당 AI 호출 1회.
          </p>
          <div className="form-group">
            <label className="form-label" htmlFor="segment-limit">
              처리할 기업 수 (비우면 전체)
            </label>
            <input
              id="segment-limit"
              className="form-input"
              type="number"
              min={1}
              inputMode="numeric"
              value={segment.limit}
              onChange={(e) => setSegment({ ...segment, limit: e.target.value })}
            />
          </div>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={segment.dry_run}
              onChange={(e) => setSegment({ ...segment, dry_run: e.target.checked })}
            />
            <span>드라이런 (대상만 확인)</span>
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={segment.relocate}
              onChange={(e) => setSegment({ ...segment, relocate: e.target.checked })}
            />
            <span>섹터에 맞는 카테고리로 폴더 이동</span>
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={segment.force}
              onChange={(e) => setSegment({ ...segment, force: e.target.checked })}
            />
            <span>이미 분류된 기업도 다시 분류</span>
          </label>
          <div className="button-row pipeline-actions">
            {startButton('segment', '세분류 실행', () =>
              withProvider({
                dry_run: segment.dry_run,
                relocate: segment.relocate,
                force: segment.force,
                ...(parseLimit(segment.limit) !== undefined && { limit: parseLimit(segment.limit) }),
              }),
            )}
          </div>
        </section>
      </div>

      <section className="glass-card" aria-labelledby="job-panel-title" style={{ marginBottom: '1.5rem' }}>
        {!shownJob && !feed?.error && (
          <>
            <h3 className="section-title visually-hidden" id="job-panel-title">
              작업 상태
            </h3>
            {jobsList.status === 'loading' || (shownId && !feed) ? (
              <LoadingState message="작업 상태를 불러오는 중..." />
            ) : jobsList.status === 'error' ? (
              <ErrorState message={jobsList.error ?? ''} onRetry={jobsList.reload} />
            ) : (
              <EmptyState
                icon={<Workflow size={28} aria-hidden="true" />}
                title="실행한 작업이 없습니다"
                hint="위에서 작업을 시작하면 진행 상황과 로그가 여기에 표시됩니다."
              />
            )}
          </>
        )}

        {feed?.error && !shownJob && <ErrorState message={feed.error} />}

        {shownJob && (
          <>
            <div className="header-row" style={{ marginBottom: '1rem' }}>
              <div>
                <h3 className="section-title" id="job-panel-title">
                  {KIND_LABELS[shownJob.kind]}
                </h3>
                <p className="form-hint" aria-live="polite">
                  <StatusBadge status={shownJob.status} /> · {formatTime(shownJob.created_at)} 시작 · 경과{' '}
                  {formatDuration(shownJob.elapsed)}
                </p>
              </div>
              {isActive(shownJob.status) && (
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => void cancel(shownJob.id)}
                >
                  <Square size={14} aria-hidden="true" />
                  작업 취소
                </button>
              )}
            </div>

            <JobProgress job={shownJob} />

            {shownJob.summary && <p className="job-summary">{shownJob.summary}</p>}
            {shownJob.error && (
              <div className="alert alert-error" style={{ margin: '0.75rem 0' }}>
                <div className="alert-body">{shownJob.error}</div>
              </div>
            )}
            {feed?.error && (
              <div className="alert alert-error" style={{ margin: '0.75rem 0' }}>
                <div className="alert-body">{feed.error}</div>
              </div>
            )}

            <JobLog lines={feed?.lines ?? []} truncated={feed?.truncated ?? false} />
          </>
        )}
      </section>

      {jobsList.data && jobsList.data.jobs.length > 0 && (
        <section className="glass-card" aria-labelledby="recent-jobs-title">
          <h3 className="section-title" id="recent-jobs-title" style={{ marginBottom: '0.75rem' }}>
            최근 작업
          </h3>
          <ul className="job-list">
            {jobsList.data.jobs.map((job) => (
              <li key={job.id}>
                <button
                  type="button"
                  className="job-item"
                  aria-current={job.id === shownId}
                  onClick={() => setSelectedId(job.id)}
                >
                  <span className="job-item-kind">{KIND_LABELS[job.kind]}</span>
                  <StatusBadge status={job.status} />
                  <span className="text-muted">{formatTime(job.created_at)}</span>
                  <span className="text-muted job-item-summary">{job.summary ?? job.error ?? ''}</span>
                </button>
              </li>
            ))}
          </ul>
          <p className="form-hint">작업 기록은 서버 메모리에만 있어 서버를 재시작하면 사라집니다.</p>
        </section>
      )}
    </div>
  );
}
