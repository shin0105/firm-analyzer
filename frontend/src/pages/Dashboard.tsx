import { apiUrl } from '../api';
import { useEffect, useState } from 'react';
import axios from 'axios';

export default function Dashboard() {
  const [stats, setStats] = useState({ total: 0 });

  useEffect(() => {
    // Assuming backend runs on 8001
    axios.get(apiUrl('/api/results/summary'))
      .then(res => setStats(res.data))
      .catch(err => console.error(err));
  }, []);

  return (
    <div className="glass-card">
      <h2 className="page-title">대시보드 (Dashboard)</h2>
      <p className="page-subtitle">기업 분석 시스템 개요</p>
      
      <div className="dashboard-grid">
        <div className="glass-card" style={{ padding: '1.5rem', background: 'rgba(255,255,255,0.03)' }}>
          <h3>분석된 총 기업 수</h3>
          <div className="dashboard-stat">{stats.total || 0} 명/개</div>
        </div>
      </div>
    </div>
  );
}
