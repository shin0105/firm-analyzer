import { useMemo, useState } from 'react';
import { AlertTriangle, Check, RotateCcw, Save } from 'lucide-react';
import { api, errorMessage } from '../lib/api';
import { useAsync } from '../lib/useAsync';
import type { AppConfig } from '../lib/types';
import { ErrorState, LoadingState, Spinner } from '../components/States';

type SaveState =
  | { kind: 'idle' }
  | { kind: 'saving' }
  | { kind: 'saved' }
  | { kind: 'failed'; message: string };

export default function ConfigPage() {
  const loaded = useAsync(async () => {
    const res = await api.get<AppConfig>('/api/config');
    return res.data;
  });

  // `draft` is null until the user edits something; the loaded config is the
  // source of truth up to that point, so no effect has to copy it into state.
  const [draft, setDraft] = useState<AppConfig | null>(null);
  const [saveState, setSaveState] = useState<SaveState>({ kind: 'idle' });
  const [confirmingReset, setConfirmingReset] = useState(false);

  const config = draft ?? loaded.data;

  // Only offer to save when something actually changed.
  const isDirty = useMemo(
    () => draft !== null && JSON.stringify(draft) !== JSON.stringify(loaded.data),
    [draft, loaded.data],
  );

  const updateSummary = (patch: Record<string, unknown>) => {
    setDraft((prev) => {
      const base = prev ?? loaded.data;
      if (!base) return prev;
      return { ...base, summary: { ...base.summary, ...patch } };
    });
    setSaveState({ kind: 'idle' });
  };

  const handleSave = async () => {
    if (!config) return;
    setSaveState({ kind: 'saving' });
    try {
      await api.post('/api/config', config);
      setSaveState({ kind: 'saved' });
      setDraft(null);
      loaded.reload();
    } catch (err) {
      setSaveState({ kind: 'failed', message: errorMessage(err) });
    }
  };

  const handleReset = async () => {
    setConfirmingReset(false);
    setSaveState({ kind: 'saving' });
    try {
      await api.post<{ success: boolean; config: AppConfig }>('/api/config/reset');
      setSaveState({ kind: 'saved' });
      setDraft(null);
      loaded.reload();
    } catch (err) {
      setSaveState({ kind: 'failed', message: errorMessage(err) });
    }
  };

  if (loaded.status === 'loading') {
    return (
      <div className="glass-card" style={{ maxWidth: '800px' }}>
        <LoadingState message="설정을 불러오는 중..." />
      </div>
    );
  }

  if (loaded.status === 'error' || !config) {
    return (
      <div className="glass-card" style={{ maxWidth: '800px' }}>
        <ErrorState message={loaded.error ?? '설정을 불러오지 못했습니다.'} onRetry={loaded.reload} />
      </div>
    );
  }

  const saving = saveState.kind === 'saving';

  return (
    <div className="glass-card" style={{ maxWidth: '800px' }}>
      <div className="page-header">
        <h2 className="page-title">설정 변경</h2>
        <p className="page-subtitle">필터 및 요약 설정</p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void handleSave();
        }}
      >
        <div className="form-group">
          <label className="form-label" htmlFor="summary-language">
            기본 프롬프트 언어
          </label>
          <input
            id="summary-language"
            className="form-input"
            type="text"
            placeholder="예: Korean"
            value={String(config.summary?.language ?? '')}
            onChange={(e) => updateSummary({ language: e.target.value })}
          />
          <p className="form-hint">요약문을 생성할 때 사용할 언어입니다. (예: Korean, English)</p>
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="summary-format">
            요약 출력 형식
          </label>
          <select
            id="summary-format"
            className="form-input"
            value={String(config.summary?.output_format ?? 'markdown')}
            onChange={(e) => updateSummary({ output_format: e.target.value })}
          >
            <option value="markdown">Markdown</option>
            <option value="json">JSON</option>
            <option value="text">Text</option>
          </select>
          <p className="form-hint">
            Markdown을 선택하면 &ldquo;요약 결과 보기&rdquo;에서 서식이 적용되어 표시됩니다.
          </p>
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="summary-prompt">
            추가 프롬프트 (선택)
          </label>
          <textarea
            id="summary-prompt"
            className="form-input"
            rows={4}
            placeholder="요약 시 강조할 내용을 자유롭게 입력하세요."
            value={String(config.summary?.custom_prompt ?? '')}
            onChange={(e) => updateSummary({ custom_prompt: e.target.value })}
          />
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
          <button type="submit" className="btn btn-primary" disabled={saving || !isDirty}>
            {saving ? <Spinner small label="저장 중" /> : <Save size={18} aria-hidden="true" />}
            {saving ? '저장 중...' : '설정 저장'}
          </button>

          {confirmingReset ? (
            <>
              <span className="form-hint" style={{ marginTop: 0 }}>
                모든 설정을 기본값으로 되돌릴까요?
              </span>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => void handleReset()}
              >
                되돌리기
              </button>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setConfirmingReset(false)}
              >
                취소
              </button>
            </>
          ) : (
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => setConfirmingReset(true)}
              disabled={saving}
            >
              <RotateCcw size={16} aria-hidden="true" />
              기본값으로 초기화
            </button>
          )}

          {isDirty && !saving && (
            <span className="form-hint" style={{ marginTop: 0 }}>
              저장하지 않은 변경사항이 있습니다.
            </span>
          )}
        </div>
      </form>

      {/* Inline, dismissible feedback instead of a blocking alert() dialog. */}
      <div aria-live="polite" style={{ marginTop: saveState.kind === 'idle' ? 0 : '1.5rem' }}>
        {saveState.kind === 'saved' && (
          <div className="alert alert-success">
            <Check size={20} aria-hidden="true" color="var(--success-color)" />
            <div>
              <div className="alert-title">저장되었습니다</div>
              <div className="alert-body">변경한 설정이 적용되었습니다.</div>
            </div>
          </div>
        )}
        {saveState.kind === 'failed' && (
          <div className="alert alert-error">
            <AlertTriangle size={20} aria-hidden="true" color="var(--danger-color)" />
            <div>
              <div className="alert-title">저장에 실패했습니다</div>
              <div className="alert-body">{saveState.message}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
