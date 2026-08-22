import { useEffect, useRef, useState } from 'react';
import {
  AlertCircle,
  CheckCircle,
  Download,
  FileText,
  UploadCloud,
  X,
} from 'lucide-react';
import { api, apiUrl, errorMessage } from '../lib/api';
import type { LLMProvider, OcrResult, ProvidersResponse } from '../lib/types';
import { Spinner } from '../components/States';

const MAX_FILE_BYTES = 50 * 1024 * 1024;

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function OcrUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [provider, setProvider] = useState<string>('');
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [result, setResult] = useState<OcrResult | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  // Which back ends this server can run, and which one config.yml selects.
  // Fetched rather than hardcoded so a provider without an API key can be
  // shown as unavailable instead of failing on upload.
  useEffect(() => {
    let cancelled = false;
    api
      .get<ProvidersResponse>('/api/llm/providers')
      .then((res) => {
        if (cancelled) return;
        setProviders(res.data.providers);
        setProvider(res.data.active);
      })
      .catch(() => {
        /* Leave the picker empty; the upload button stays disabled. */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedProvider = providers.find((p) => p.id === provider);
  const providerLabel = selectedProvider?.label ?? provider;

  /** Validate before the user waits on a doomed upload. */
  const acceptFile = (candidate: File | undefined) => {
    if (!candidate) return;
    setResult(null);

    if (!candidate.name.toLowerCase().endsWith('.pdf') && candidate.type !== 'application/pdf') {
      setValidationError('PDF 파일만 업로드할 수 있습니다.');
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
  };

  const clearFile = () => {
    setFile(null);
    setValidationError(null);
    setResult(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setProgress(0);
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('provider', provider);

    try {
      const res = await api.post<OcrResult>('/api/upload-pdf', formData, {
        // OCR runs an LLM over the whole document, so allow far longer than
        // the default request timeout.
        timeout: 10 * 60 * 1000,
        onUploadProgress: (event) => {
          if (event.total) setProgress(Math.round((event.loaded / event.total) * 100));
        },
      });
      setResult(res.data);
    } catch (err) {
      setResult({ success: false, error: errorMessage(err) });
    } finally {
      setLoading(false);
      setProgress(0);
    }
  };

  return (
    <div className="glass-card" style={{ maxWidth: '640px', margin: '0 auto' }}>
      <div className="page-header">
        <h2 className="page-title">PDF OCR 변환</h2>
        <p className="page-subtitle">
          PDF 문서를 업로드하여 AI로 CSV 데이터로 변환합니다.
        </p>
      </div>

      {/* A real button, so the dropzone is reachable by keyboard too. */}
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
        aria-describedby="dropzone-hint"
      >
        <UploadCloud size={44} color="var(--accent-color)" aria-hidden="true" />
        <span style={{ fontWeight: 600 }}>
          {file ? '다른 파일 선택' : 'PDF 파일을 끌어다 놓거나 클릭해 선택하세요'}
        </span>
        <span className="dropzone-hint" id="dropzone-hint">
          PDF 형식, 최대 {formatBytes(MAX_FILE_BYTES)}
        </span>
      </button>

      <input
        ref={inputRef}
        id="pdf-upload"
        type="file"
        accept="application/pdf,.pdf"
        className="visually-hidden"
        onChange={(e) => acceptFile(e.target.files?.[0])}
      />

      <div aria-live="polite">
        {validationError && (
          <div className="alert alert-error" style={{ marginTop: '1rem' }}>
            <AlertCircle size={20} aria-hidden="true" color="var(--danger-color)" />
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

      <div className="form-group" style={{ marginTop: '1.5rem' }}>
        <label className="form-label" htmlFor="ocr-provider">
          AI 모델 선택
        </label>
        <select
          id="ocr-provider"
          className="form-input"
          value={provider}
          onChange={(e) => setProvider(e.target.value)}
          disabled={loading || providers.length === 0}
        >
          {providers.map((p) => (
            <option key={p.id} value={p.id} disabled={!p.configured}>
              {p.label} ({p.parser_model})
              {p.configured ? '' : ' — API 키 없음'}
            </option>
          ))}
        </select>
        {selectedProvider && (
          <p className="form-hint">
            {selectedProvider.supports_native_pdf
              ? 'PDF를 그대로 읽습니다. 스캔 문서도 처리할 수 있습니다.'
              : 'PDF에서 텍스트를 추출해 전달합니다. 스캔 문서는 인식되지 않습니다.'}
          </p>
        )}
      </div>

      <button
        type="button"
        className="btn btn-primary btn-block"
        style={{ padding: '1rem' }}
        onClick={() => void handleUpload()}
        disabled={!file || loading || !selectedProvider?.configured}
      >
        {loading ? (
          <>
            <Spinner small label="변환 중" />
            {progress > 0 && progress < 100 ? `업로드 중 ${progress}%` : `${providerLabel} 분석 중...`}
          </>
        ) : (
          'CSV 변환 시작'
        )}
      </button>

      {loading && (
        <p className="form-hint" style={{ textAlign: 'center' }}>
          문서 길이에 따라 몇 분이 걸릴 수 있습니다. 이 페이지를 열어 두세요.
        </p>
      )}

      <div aria-live="polite">
        {result && (
          <div
            className={`alert ${result.success ? 'alert-success' : 'alert-error'}`}
            style={{ marginTop: '1.5rem', flexDirection: 'column' }}
          >
            {result.success ? (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <CheckCircle size={22} aria-hidden="true" color="var(--success-color)" />
                  <strong className="alert-title" style={{ fontSize: '1.1rem' }}>
                    변환 성공
                  </strong>
                </div>
                <p className="alert-body">{result.message}</p>
                {result.output_file && (
                  <a
                    href={apiUrl(`/api/download/${encodeURIComponent(result.output_file)}`)}
                    className="btn btn-primary btn-sm"
                    download
                  >
                    <Download size={16} aria-hidden="true" />
                    {result.output_file} 다운로드
                  </a>
                )}
              </>
            ) : (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <AlertCircle size={22} aria-hidden="true" color="var(--danger-color)" />
                  <strong className="alert-title" style={{ fontSize: '1.1rem' }}>
                    오류 발생
                  </strong>
                </div>
                <p className="alert-body">{result.error}</p>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
