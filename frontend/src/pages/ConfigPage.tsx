import { apiUrl, type AppConfig, type LLMProvider, type ProvidersResponse } from '../api';
import { useEffect, useState } from 'react';
import axios from 'axios';
import { AlertCircle, Check } from 'lucide-react';

export default function ConfigPage() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [providers, setProviders] = useState<LLMProvider[]>([]);

  useEffect(() => {
    axios.get(apiUrl('/api/config'))
      .then(res => setConfig(res.data))
      .catch(err => console.error(err));

    axios.get<ProvidersResponse>(apiUrl('/api/llm/providers'))
      .then(res => setProviders(res.data.providers))
      .catch(err => console.error(err));
  }, []);

  const handleSave = () => {
    axios.post(apiUrl('/api/config'), config)
      .then(() => alert('저장되었습니다!'))
      .catch(err => alert('오류: ' + err.message));
  };

  if (!config) return <div>로딩 중...</div>;

  const selectedProviderId = config.app?.llm_provider ?? providers.find(p => p.active)?.id ?? 'openai';
  const selected = providers.find(p => p.id === selectedProviderId);

  const setProvider = (id: string) => {
    setConfig({ ...config, app: { ...config.app, llm_provider: id } });
  };

  const setModelOverride = (id: string, model: string) => {
    setConfig({
      ...config,
      app: { ...config.app, llm_models: { ...(config.app?.llm_models ?? {}), [id]: model } },
    });
  };

  return (
    <div className="glass-card" style={{ maxWidth: '800px' }}>
      <h2 className="page-title">설정 변경</h2>
      <p className="page-subtitle">AI 모델, 필터 및 요약 설정</p>

      <div className="form-group">
        <label className="form-label">사용할 AI (LLM Provider)</label>
        <select
          className="form-input"
          value={selectedProviderId}
          onChange={e => setProvider(e.target.value)}
        >
          {providers.map(p => (
            <option key={p.id} value={p.id}>
              {p.label}{p.configured ? '' : ' — API 키 없음'}
            </option>
          ))}
        </select>

        {selected && (
          <div
            style={{
              marginTop: '0.75rem',
              padding: '0.75rem 1rem',
              borderRadius: '0.5rem',
              display: 'flex',
              gap: '0.5rem',
              alignItems: 'flex-start',
              background: selected.configured ? 'rgba(16, 185, 129, 0.08)' : 'rgba(239, 68, 68, 0.08)',
              border: `1px solid ${selected.configured ? 'var(--success-color)' : 'var(--danger-color)'}`,
            }}
          >
            {selected.configured
              ? <Check size={18} color="var(--success-color)" style={{ flexShrink: 0, marginTop: 2 }} />
              : <AlertCircle size={18} color="var(--danger-color)" style={{ flexShrink: 0, marginTop: 2 }} />}
            <div style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>
              {selected.configured
                ? <>기본 모델 <code>{selected.model}</code> · PDF 파싱 <code>{selected.parser_model}</code></>
                : <><code>{selected.key_env}</code> 값을 <code>.env</code> 파일에 추가해야 사용할 수 있습니다.</>}
              {selected.notes && (
                <div style={{ opacity: 0.75, marginTop: '0.25rem' }}>{selected.notes}</div>
              )}
            </div>
          </div>
        )}
      </div>

      {selected && (
        <div className="form-group">
          <label className="form-label">모델 직접 지정 (비워두면 기본값)</label>
          <input
            className="form-input"
            type="text"
            placeholder={selected.model}
            value={config.app?.llm_models?.[selected.id] ?? ''}
            onChange={e => setModelOverride(selected.id, e.target.value)}
          />
        </div>
      )}

      <div className="form-group">
        <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <input
            type="checkbox"
            checked={config.segmentation?.enabled ?? true}
            onChange={e => setConfig({
              ...config,
              segmentation: { ...config.segmentation, enabled: e.target.checked },
            })}
          />
          세분류(다축 분류) 사용 — taxonomy.yml 기준
        </label>
      </div>

      <div className="form-group">
        <label className="form-label">기본 프롬프트 언어</label>
        <input
          className="form-input"
          type="text"
          value={config.summary?.language || ''}
          onChange={e => setConfig({...config, summary: {...config.summary, language: e.target.value}})}
        />
      </div>

      <div className="form-group">
        <label className="form-label">요약 출력 형식</label>
        <select
          className="form-input"
          value={config.summary?.output_format || 'markdown'}
          onChange={e => setConfig({...config, summary: {...config.summary, output_format: e.target.value}})}
        >
          <option value="markdown">Markdown</option>
          <option value="json">JSON</option>
          <option value="text">Text</option>
        </select>
      </div>

      <button className="btn btn-primary" onClick={handleSave}>설정 저장</button>
    </div>
  );
}
