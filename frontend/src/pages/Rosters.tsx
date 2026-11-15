import { useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import {
  AlertCircle,
  CheckCircle,
  Download,
  FileText,
  GitCompare,
  ListChecks,
  Play,
  RotateCw,
  UploadCloud,
  X,
} from 'lucide-react';
import { api, apiUrl, errorMessage } from '../lib/api';
import { useAsync } from '../lib/useAsync';
import type {
  ProvidersResponse,
  RosterDiff,
  RosterImportResult,
  RosterInfo,
  RosterRow,
  RostersResponse,
} from '../lib/types';
import { EmptyState, ErrorState, LoadingState, Spinner } from '../components/States';

const MAX_FILE_BYTES = 32 * 1024 * 1024;
/** Rows shown per side of a comparison before "모두 보기". */
const PREVIEW_ROWS = 30;

type Method = 'rule' | 'llm';

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(epochSeconds: number): string {
  return new Date(epochSeconds * 1000).toLocaleDateString('ko-KR');
}

/** "2027_전문연구요원_인원배정.pdf" -> "2027", so the year field fills itself. */
function yearFromName(name: string): string {
  return name.match(/(20\d{2})/)?.[1] ?? '';
}

function compareUrl(diff: RosterDiff, part?: 'added' | 'removed'): string {
  const params = new URLSearchParams({ base: diff.base, target: diff.target });
  if (part) params.set('part', part);
  return apiUrl(`/api/rosters/compare${part ? '.csv' : ''}?${params}`);
}

function RosterTable({ rows, caption }: { rows: RosterRow[]; caption: string }) {
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? rows : rows.slice(0, PREVIEW_ROWS);
  return (
    <>
      <div className="table-scroll">
        <table className="data-table">
          <caption className="visually-hidden">{caption}</caption>
          <thead>
            <tr>
              <th scope="col">업체명</th>
              <th scope="col">업종구분</th>
              <th scope="col">소재지</th>
              <th scope="col">배정인원</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((row, index) => (
              <tr key={`${row['업체명']}-${index}`}>
                <td>{row['업체명']}</td>
                <td>{row['업종구분'] ?? ''}</td>
                <td>{row['소재지']}</td>
                <td>{row['배정인원'] ?? ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length > PREVIEW_ROWS && (
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setExpanded((v) => !v)}>
          {expanded ? '접기' : `${(rows.length - PREVIEW_ROWS).toLocaleString('ko-KR')}개 더 보기`}
        </button>
      )}
    </>
  );
}

/** Counts, both sides as tables, CSV downloads, and what to do next. */
function DiffView({ diff, showNextStep }: { diff: RosterDiff; showNextStep: boolean }) {
  const { counts } = diff;
  return (
    <div className="diff-view">
      <p className="form-hint">
        <code>{diff.base}</code> → <code>{diff.target}</code>
      </p>
      <div className="stat-chips" role="group" aria-label="비교 결과">
        <span className="stat-chip" data-kind="added">
          신규 <strong>+{counts.added.toLocaleString('ko-KR')}</strong>
        </span>
        <span className="stat-chip" data-kind="removed">
          제외 <strong>−{counts.removed.toLocaleString('ko-KR')}</strong>
        </span>
        <span className="stat-chip">
          유지 <strong>{counts.kept.toLocaleString('ko-KR')}</strong>
        </span>
      </div>

      {showNextStep && counts.added > 0 && (
        <div className="alert" style={{ margin: '1rem 0' }}>
          <Play size={18} aria-hidden="true" color="var(--color-pen)" />
          <div className="alert-body">
            새로 추가된 기업만 요약하려면 <Link to="/pipeline">파이프라인 실행</Link>에서 &lsquo;필터 후
            요약&rsquo;을 실행하세요. 이미 요약한 기업은 자동으로 건너뜁니다.
          </div>
        </div>
      )}

      {(['added', 'removed'] as const).map((part) => {
        const rows = part === 'added' ? diff.added : diff.removed;
        const title = part === 'added' ? '새로 추가된 기업' : '명단에서 빠진 기업';
        return (
          <section key={part} className="diff-section" aria-label={title}>
            <div className="header-row" style={{ marginBottom: '0.5rem', alignItems: 'center' }}>
              <h4 className="diff-title">
                {title} ({rows.length.toLocaleString('ko-KR')})
              </h4>
              {rows.length > 0 && (
                <a className="btn btn-secondary btn-sm" href={compareUrl(diff, part)} download>
                  <Download size={14} aria-hidden="true" />
                  CSV
                </a>
              )}
            </div>
            {rows.length > 0 ? (
              <RosterTable rows={rows} caption={title} />
            ) : (
              <p className="form-hint">없음</p>
            )}
          </section>
        );
      })}
      <p className="form-hint">
        기업은 이름으로 대조합니다. (주)·주식회사 같은 법인 표기와 띄어쓰기는 무시하지만, 연구소 이름이
        바뀐 경우에는 제외+신규로 함께 표시될 수 있습니다.
      </p>
    </div>
  );
}

function ImportCard({ onImported }: { onImported: () => void }) {
  const providers = useAsync(async () => (await api.get<ProvidersResponse>('/api/llm/providers')).data);
  const [file, setFile] = useState<File | null>(null);
  const [year, setYear] = useState('');
  const [method, setMethod] = useState<Method>('rule');
  const [provider, setProvider] = useState('');
  const [activate, setActivate] = useState(true);
  const [overwrite, setOverwrite] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RosterImportResult | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const providerList = providers.data?.providers ?? [];
  const chosenProvider = providerList.find((p) => p.id === (provider || providers.data?.active));
  const isPdf = file?.name.toLowerCase().endsWith('.pdf') ?? false;
  const needsKey = isPdf && method === 'llm' && chosenProvider?.configured === false;

  const acceptFile = (candidate: File | undefined) => {
    if (!candidate) return;
    setResult(null);
    setError(null);
    const name = candidate.name.toLowerCase();
    if (!name.endsWith('.pdf') && !name.endsWith('.csv')) {
      setValidationError('PDF 또는 CSV 파일만 가져올 수 있습니다.');
      setFile(null);
      return;
    }
    if (candidate.size > MAX_FILE_BYTES) {
      setValidationError(`파일이 너무 큽니다. 최대 ${formatBytes(MAX_FILE_BYTES)}까지 지원합니다.`);
      setFile(null);
      return;
    }
    setValidationError(null);
    setFile(candidate);
    setYear(yearFromName(candidate.name));
  };

  const clearFile = () => {
    setFile(null);
    setYear('');
    setValidationError(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  const submit = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    const form = new FormData();
    form.append('file', file);
    if (year.trim()) form.append('year', year.trim());
    form.append('method', method);
    if (method === 'llm' && provider) form.append('provider', provider);
    form.append('activate', String(activate));
    form.append('overwrite', String(overwrite));
    try {
      const res = await api.post<RosterImportResult>('/api/rosters/import', form, {
        // The AI method reads the PDF in several requests; allow minutes.
        timeout: method === 'llm' && isPdf ? 15 * 60 * 1000 : 2 * 60 * 1000,
      });
      setResult(res.data);
      clearFile();
      onImported();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="glass-card" aria-labelledby="import-title" style={{ marginBottom: '1.5rem' }}>
      <h3 className="section-title" id="import-title" style={{ marginBottom: '0.25rem' }}>
        새 명단 가져오기
      </h3>
      <p className="form-hint" style={{ marginBottom: '1rem' }}>
        병무청 누리집에서 받은 인원배정 PDF를 그대로 올리거나, <code>업체명</code>·<code>소재지</code>{' '}
        열이 있는 CSV를 올리세요. <code>data/&lt;연도&gt;_전문연구요원_인원배정.csv</code>로 저장됩니다.
      </p>

      <button
        type="button"
        className="dropzone"
        data-dragging={dragging}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          acceptFile(e.dataTransfer.files?.[0]);
        }}
        aria-describedby="roster-dropzone-hint"
        disabled={loading}
      >
        <UploadCloud size={40} color="var(--color-pen)" aria-hidden="true" />
        <span style={{ fontWeight: 600 }}>
          {file ? '다른 파일 선택' : 'PDF 또는 CSV를 끌어다 놓거나 클릭해 선택하세요'}
        </span>
        <span className="dropzone-hint" id="roster-dropzone-hint">
          최대 {formatBytes(MAX_FILE_BYTES)} · CSV는 UTF-8 또는 CP949(엑셀 기본) 인코딩
        </span>
      </button>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.csv,application/pdf,text/csv"
        className="visually-hidden"
        onChange={(e) => acceptFile(e.target.files?.[0])}
        aria-label="명단 파일 선택"
      />

      <div aria-live="polite">
        {validationError && (
          <div className="alert alert-error" style={{ marginTop: '1rem' }}>
            <AlertCircle size={20} aria-hidden="true" color="var(--color-redpen)" />
            <div className="alert-body">{validationError}</div>
          </div>
        )}
        {file && (
          <div className="file-pill" style={{ marginTop: '1rem' }}>
            <FileText size={18} aria-hidden="true" />
            <span className="file-pill-name">{file.name}</span>
            <span className="file-pill-size">{formatBytes(file.size)}</span>
            <button
              type="button"
              className="btn-icon"
              onClick={clearFile}
              aria-label={`선택한 파일 ${file.name} 제거`}
              style={{ marginLeft: 'auto' }}
              disabled={loading}
            >
              <X size={16} aria-hidden="true" />
            </button>
          </div>
        )}
      </div>

      <div className="import-options">
        <div className="form-group">
          <label className="form-label" htmlFor="roster-year">
            명단 연도
          </label>
          <input
            id="roster-year"
            className="form-input"
            type="number"
            inputMode="numeric"
            min={2000}
            max={2100}
            placeholder="예: 2027"
            value={year}
            onChange={(e) => setYear(e.target.value)}
            disabled={loading}
          />
          <p className="form-hint">파일 이름에 연도가 있으면 자동으로 채워집니다.</p>
        </div>

        {(isPdf || !file) && (
          <fieldset className="form-group" disabled={loading}>
            <legend className="form-label">PDF 추출 방식</legend>
            <label className="checkbox-row">
              <input type="radio" name="method" checked={method === 'rule'} onChange={() => setMethod('rule')} />
              <span>표 인식 (권장 · 무료 · 몇 초)</span>
            </label>
            <label className="checkbox-row">
              <input type="radio" name="method" checked={method === 'llm'} onChange={() => setMethod('llm')} />
              <span>AI로 추출 (스캔 PDF용 · API 비용 발생 · 몇 분)</span>
            </label>
          </fieldset>
        )}

        {isPdf && method === 'llm' && (
          <div className="form-group">
            <label className="form-label" htmlFor="roster-provider">
              AI 모델
            </label>
            <select
              id="roster-provider"
              className="form-input"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              disabled={loading || providers.status !== 'success'}
            >
              <option value="">config.yml 기본값</option>
              {providerList.map((p) => (
                <option key={p.id} value={p.id} disabled={!p.configured}>
                  {p.label} ({p.parser_model}){p.configured ? '' : ' — API 키 없음'}
                </option>
              ))}
            </select>
            {needsKey && (
              <p className="form-hint" role="alert">
                선택한 AI의 API 키가 서버에 없습니다.
              </p>
            )}
          </div>
        )}
      </div>

      <label className="checkbox-row">
        <input type="checkbox" checked={activate} onChange={(e) => setActivate(e.target.checked)} disabled={loading} />
        <span>가져온 뒤 이 명단을 파이프라인 입력으로 사용</span>
      </label>
      <label className="checkbox-row" style={{ marginTop: '0.5rem' }}>
        <input type="checkbox" checked={overwrite} onChange={(e) => setOverwrite(e.target.checked)} disabled={loading} />
        <span>같은 연도의 명단이 이미 있으면 덮어쓰기</span>
      </label>

      <button
        type="button"
        className="btn btn-primary btn-block"
        style={{ marginTop: '1.25rem', padding: '0.9rem' }}
        onClick={() => void submit()}
        disabled={!file || loading || needsKey}
      >
        {loading ? (
          <>
            <Spinner small label="가져오는 중" />
            {method === 'llm' && isPdf ? 'AI가 PDF를 읽는 중... (몇 분 걸릴 수 있습니다)' : '명단을 읽는 중...'}
          </>
        ) : (
          '가져오기'
        )}
      </button>

      <div aria-live="polite">
        {error && (
          <div className="alert alert-error" style={{ marginTop: '1rem' }}>
            <AlertCircle size={20} aria-hidden="true" color="var(--color-redpen)" />
            <div>
              <strong className="alert-title">가져오지 못했습니다</strong>
              <div className="alert-body">{error}</div>
            </div>
          </div>
        )}
        {result && (
          <div className="import-result">
            <div className="alert alert-success" style={{ marginTop: '1rem' }}>
              <CheckCircle size={20} aria-hidden="true" color="var(--color-ok)" />
              <div>
                <strong className="alert-title">
                  {result.roster.name} · {result.roster.rows.toLocaleString('ko-KR')}개 기업
                </strong>
                <div className="alert-body">
                  {result.activated
                    ? '이제 필터 단계가 이 명단을 읽습니다.'
                    : '저장했습니다. 아래 목록에서 언제든 사용할 명단으로 바꿀 수 있습니다.'}
                </div>
              </div>
            </div>
            {result.warnings.length > 0 && (
              <div className="alert alert-warning" style={{ marginTop: '0.75rem' }}>
                <AlertCircle size={20} aria-hidden="true" color="var(--color-warn)" />
                <div>
                  <strong className="alert-title">확인이 필요합니다</strong>
                  <ul className="alert-body">
                    {result.warnings.map((w) => (
                      <li key={w}>{w}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
            {result.diff ? (
              <>
                <h4 className="diff-title" style={{ marginTop: '1.25rem' }}>
                  이전 명단과 비교
                </h4>
                <DiffView diff={result.diff} showNextStep={result.activated} />
              </>
            ) : (
              <p className="form-hint" style={{ marginTop: '0.75rem' }}>
                비교할 이전 명단이 없습니다.
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

function CompareCard({ rosters }: { rosters: RosterInfo[] }) {
  const [baseChoice, setBase] = useState<string | null>(null);
  const [targetChoice, setTarget] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [diff, setDiff] = useState<RosterDiff | null>(null);

  // Default to the newest list against the one before it, and fall back to
  // that whenever a chosen list disappears (e.g. the list reloads).
  const names = useMemo(() => rosters.map((r) => r.name), [rosters]);
  const target = targetChoice && names.includes(targetChoice) ? targetChoice : (names[0] ?? '');
  const base = baseChoice && names.includes(baseChoice) ? baseChoice : (names[1] ?? '');

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<RosterDiff>('/api/rosters/compare', { params: { base, target } });
      setDiff(res.data);
    } catch (err) {
      setError(errorMessage(err));
      setDiff(null);
    } finally {
      setLoading(false);
    }
  };

  if (rosters.length < 2) return null;

  return (
    <section className="glass-card" aria-labelledby="compare-title" style={{ marginBottom: '1.5rem' }}>
      <h3 className="section-title" id="compare-title" style={{ marginBottom: '1rem' }}>
        명단 비교
      </h3>
      <div className="compare-row">
        <div className="form-group">
          <label className="form-label" htmlFor="compare-base">
            기준 (이전)
          </label>
          <select id="compare-base" className="form-input" value={base} onChange={(e) => setBase(e.target.value)}>
            {names.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor="compare-target">
            비교 대상 (새)
          </label>
          <select id="compare-target" className="form-input" value={target} onChange={(e) => setTarget(e.target.value)}>
            {names.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => void run()}
          disabled={loading || !base || !target || base === target}
        >
          {loading ? <Spinner small label="비교 중" /> : <GitCompare size={16} aria-hidden="true" />}
          비교
        </button>
      </div>
      <div aria-live="polite">
        {error && (
          <div className="alert alert-error">
            <div className="alert-body">{error}</div>
          </div>
        )}
        {diff && <DiffView diff={diff} showNextStep={false} />}
      </div>
    </section>
  );
}

export default function Rosters() {
  const rosters = useAsync(async () => (await api.get<RostersResponse>('/api/rosters')).data);
  const [activating, setActivating] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const list = rosters.data?.rosters ?? [];
  const active = list.find((r) => r.active);

  const activate = async (name: string) => {
    setActivating(name);
    setActionError(null);
    try {
      await api.post('/api/rosters/active', { name });
      rosters.reload();
    } catch (err) {
      const busy = axios.isAxiosError(err) && err.response?.status === 409;
      setActionError(busy ? '파이프라인 작업이 실행 중이라 명단을 바꿀 수 없습니다. 작업이 끝난 뒤 다시 시도하세요.' : errorMessage(err));
    } finally {
      setActivating(null);
    }
  };

  return (
    <div>
      <div className="header-row">
        <div className="page-header">
          <h2 className="page-title">전문연 명단 관리</h2>
          <p className="page-subtitle">
            병무청이 매년 발표하는 전문연구요원 인원배정 명단을 가져오고, 이전 명단과 비교하고, 파이프라인이
            읽을 명단을 고릅니다
          </p>
        </div>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={rosters.reload}
          disabled={rosters.status === 'loading'}
        >
          <RotateCw size={16} aria-hidden="true" />
          새로고침
        </button>
      </div>

      <div className="glass-card card-tight active-roster" style={{ marginBottom: '1.5rem' }}>
        <ListChecks size={22} aria-hidden="true" color="var(--color-pen)" />
        {rosters.status === 'loading' ? (
          <span className="text-muted">현재 명단을 확인하는 중...</span>
        ) : active ? (
          <div>
            <div className="stat-card-label">현재 파이프라인 입력 명단</div>
            <strong>{active.name}</strong>{' '}
            <span className="text-muted">
              · {active.rows.toLocaleString('ko-KR')}개 기업{active.year ? ` · ${active.year}년` : ''}
            </span>
          </div>
        ) : (
          <span>아직 명단이 없습니다. 아래에서 인원배정 PDF를 가져오세요.</span>
        )}
      </div>

      <ImportCard onImported={rosters.reload} />

      {rosters.status === 'success' && <CompareCard rosters={list} />}

      <section className="glass-card" aria-labelledby="rosters-title">
        <h3 className="section-title" id="rosters-title" style={{ marginBottom: '1rem' }}>
          저장된 명단
        </h3>
        <div aria-live="polite">
          {actionError && (
            <div className="alert alert-error" style={{ marginBottom: '1rem' }}>
              <div className="alert-body">{actionError}</div>
            </div>
          )}
        </div>
        {rosters.status === 'loading' && <LoadingState message="명단을 불러오는 중..." />}
        {rosters.status === 'error' && <ErrorState message={rosters.error ?? ''} onRetry={rosters.reload} />}
        {rosters.status === 'success' && list.length === 0 && (
          <EmptyState title="저장된 명단이 없습니다" hint="위에서 인원배정 PDF나 CSV를 가져오세요." />
        )}
        {list.length > 0 && (
          <div className="table-scroll">
            <table className="data-table">
              <caption className="visually-hidden">data 폴더의 명단</caption>
              <thead>
                <tr>
                  <th scope="col">파일</th>
                  <th scope="col">연도</th>
                  <th scope="col">기업 수</th>
                  <th scope="col">수정일</th>
                  <th scope="col">
                    <span className="visually-hidden">작업</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {list.map((r) => (
                  <tr key={r.name} aria-current={r.active || undefined}>
                    <td>
                      {r.name}
                      {r.active && <span className="status-badge" data-status="succeeded">사용 중</span>}
                    </td>
                    <td>{r.year ?? '—'}</td>
                    <td>{r.rows.toLocaleString('ko-KR')}</td>
                    <td>{formatDate(r.modified)}</td>
                    <td>
                      <div className="button-row" style={{ justifyContent: 'flex-end' }}>
                        {!r.active && (
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            onClick={() => void activate(r.name)}
                            disabled={activating !== null}
                          >
                            {activating === r.name ? <Spinner small label="변경 중" /> : null}
                            사용하기
                          </button>
                        )}
                        <a
                          className="btn btn-ghost btn-sm"
                          href={apiUrl(`/api/rosters/${encodeURIComponent(r.name)}/download`)}
                          download
                          aria-label={`${r.name} 다운로드`}
                        >
                          <Download size={14} aria-hidden="true" />
                        </a>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
