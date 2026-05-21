import { useState } from 'react';
import axios from 'axios';
import { UploadCloud, File, CheckCircle, AlertCircle } from 'lucide-react';

export default function OcrUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [provider, setProvider] = useState<string>('gemini');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{success: boolean, message?: string, output_file?: string, error?: string} | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('provider', provider);

    try {
      const res = await axios.post('http://localhost:8001/api/upload-pdf', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setResult(res.data);
    } catch (err: any) {
      setResult({
        success: false,
        error: err.response?.data?.error || err.message
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-card" style={{ maxWidth: '600px', margin: '0 auto' }}>
      <h2 className="page-title">PDF OCR 변환</h2>
      <p className="page-subtitle">PDF 문서를 업로드하여 Gemini AI를 통해 CSV 데이터로 변환합니다.</p>
      
      <div 
        style={{ 
          border: '2px dashed var(--surface-border)', 
          borderRadius: '1rem', 
          padding: '3rem 2rem', 
          textAlign: 'center',
          marginBottom: '1.5rem',
          background: 'rgba(255,255,255,0.02)',
          transition: 'border 0.2s',
          cursor: 'pointer'
        }}
        onClick={() => document.getElementById('pdf-upload')?.click()}
      >
        <UploadCloud size={48} color="var(--accent-color)" style={{ marginBottom: '1rem', margin: '0 auto' }} />
        <div style={{ marginBottom: '1rem' }}>
          <span className="btn btn-secondary" style={{ pointerEvents: 'none' }}>
            파일 선택
          </span>
          <input id="pdf-upload" type="file" accept=".pdf" style={{ display: 'none' }} onChange={handleFileChange} />
        </div>
        {file && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', color: 'var(--success-color)' }}>
            <File size={20} />
            <span>{file.name}</span>
          </div>
        )}
      </div>

      <div className="form-group" style={{ marginBottom: '1.5rem' }}>
        <label className="form-label" style={{ textAlign: 'left', display: 'block' }}>AI 모델 선택 (AI Provider)</label>
        <select 
          className="form-input" 
          value={provider} 
          onChange={(e) => setProvider(e.target.value)}
        >
          <option value="gemini">Gemini (3.1 Flash Lite)</option>
          <option value="openai">OpenAI (GPT-5-mini)</option>
        </select>
      </div>

      <button 
        className="btn btn-primary" 
        style={{ width: '100%', padding: '1rem', fontSize: '1.1rem' }} 
        onClick={handleUpload}
        disabled={!file || loading}
      >
        {loading ? '변환 중... (Gemini AI가 문서를 분석 중입니다)' : 'CSV 변환 시작'}
      </button>

      {result && (
        <div style={{ 
          marginTop: '1.5rem', 
          padding: '1.5rem', 
          borderRadius: '0.75rem',
          background: result.success ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
          border: `1px solid ${result.success ? 'var(--success-color)' : 'var(--danger-color)'}`
        }}>
          {result.success ? (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--success-color)', marginBottom: '0.5rem' }}>
                <CheckCircle size={24} />
                <strong style={{ fontSize: '1.2rem' }}>변환 성공!</strong>
              </div>
              <p style={{ color: 'var(--text-primary)', marginBottom: '1rem' }}>{result.message}</p>
              {result.output_file && (
                <a 
                  href={`http://localhost:8001/api/download/${result.output_file}`}
                  className="btn btn-primary"
                  style={{ display: 'inline-flex' }}
                >
                  {result.output_file} 다운로드
                </a>
              )}
            </div>
          ) : (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--danger-color)', marginBottom: '0.5rem' }}>
                <AlertCircle size={24} />
                <strong style={{ fontSize: '1.2rem' }}>오류 발생</strong>
              </div>
              <p style={{ color: 'var(--text-primary)' }}>{result.error}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
