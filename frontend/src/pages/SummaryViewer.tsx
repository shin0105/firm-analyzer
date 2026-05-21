import { useEffect, useState } from 'react';
import axios from 'axios';

export default function SummaryViewer() {
  const [categories, setCategories] = useState<any[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [firms, setFirms] = useState<any[]>([]);
  const [selectedFirm, setSelectedFirm] = useState<any>(null);

  useEffect(() => {
    axios.get('http://localhost:8001/api/results/summary')
      .then(res => {
        const cats = Object.keys(res.data).filter(k => k !== 'total').map(k => ({
          id: k,
          ...res.data[k]
        }));
        setCategories(cats);
        if (cats.length > 0) setSelectedCategory(cats[0].id);
      })
      .catch(err => console.error(err));
  }, []);

  useEffect(() => {
    if (selectedCategory) {
      axios.get(`http://localhost:8001/api/results/${selectedCategory}`)
        .then(res => setFirms(res.data.firms))
        .catch(err => console.error(err));
    }
  }, [selectedCategory]);

  return (
    <div style={{ display: 'flex', gap: '2rem', height: 'calc(100vh - 5rem)' }}>
      <div className="glass-card" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <h2 className="page-title" style={{ fontSize: '1.5rem' }}>카테고리 및 기업</h2>
        
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
          {categories.map(cat => (
            <button 
              key={cat.id} 
              className={selectedCategory === cat.id ? "btn btn-primary" : "btn btn-secondary"}
              onClick={() => setSelectedCategory(cat.id)}
              style={{ padding: '0.5rem 1rem', fontSize: '0.9rem' }}
            >
              {cat.name} ({cat.count})
            </button>
          ))}
        </div>

        <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem', paddingRight: '0.5rem' }}>
          {firms.map((firm, idx) => (
            <div 
              key={idx} 
              style={{ 
                padding: '1rem', 
                background: selectedFirm?.name === firm.name ? 'rgba(59, 130, 246, 0.2)' : 'rgba(255, 255, 255, 0.05)', 
                borderRadius: '0.5rem',
                cursor: 'pointer',
                transition: 'background 0.2s',
                border: selectedFirm?.name === firm.name ? '1px solid rgba(59, 130, 246, 0.4)' : '1px solid transparent'
              }}
              onClick={() => setSelectedFirm(firm)}
            >
              {firm.name}
            </div>
          ))}
          {firms.length === 0 && <div style={{ color: 'var(--text-secondary)' }}>해당 카테고리에 기업이 없습니다.</div>}
        </div>
      </div>

      <div className="glass-card" style={{ flex: 2, overflowY: 'auto' }}>
        <h2 className="page-title" style={{ fontSize: '1.5rem' }}>{selectedFirm ? selectedFirm.name : '기업을 선택하세요'}</h2>
        {selectedFirm && (
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.6', background: 'rgba(15, 23, 42, 0.6)', padding: '1.5rem', borderRadius: '0.5rem', marginTop: '1rem', border: '1px solid var(--surface-border)' }}>
            {selectedFirm.summary || '요약 내용이 없습니다.'}
          </div>
        )}
      </div>
    </div>
  );
}
