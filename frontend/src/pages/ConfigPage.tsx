import { apiUrl, type AppConfig } from '../api';
import { useEffect, useState } from 'react';
import axios from 'axios';

export default function ConfigPage() {
  const [config, setConfig] = useState<AppConfig | null>(null);

  useEffect(() => {
    axios.get(apiUrl('/api/config'))
      .then(res => setConfig(res.data))
      .catch(err => console.error(err));
  }, []);

  const handleSave = () => {
    axios.post(apiUrl('/api/config'), config)
      .then(() => alert('저장되었습니다!'))
      .catch(err => alert('오류: ' + err.message));
  };

  if (!config) return <div>로딩 중...</div>;

  return (
    <div className="glass-card" style={{ maxWidth: '800px' }}>
      <h2 className="page-title">설정 변경</h2>
      <p className="page-subtitle">필터 및 요약 설정</p>
      
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
