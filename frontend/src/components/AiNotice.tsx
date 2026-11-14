import { Link, useLocation } from 'react-router-dom';
import { ShieldAlert } from 'lucide-react';

/**
 * The label on every view of AI-written firm content. Same wording as
 * `AI_NOTICE_KO` in `src/firm_analyzer/notice.py`; keep the two in step.
 */
export const AI_NOTICE_TEXT =
  '이 요약은 공개 웹 검색 결과를 바탕으로 AI가 자동 생성한 참고 자료입니다. ' +
  '사실과 다르거나 오래된 정보, 동명의 다른 기업 정보가 섞여 있을 수 있으며, ' +
  '해당 기업의 공식 입장이나 평가가 아닙니다. 지원·투자 등 중요한 결정 전에는 ' +
  '반드시 기업의 공식 채널에서 직접 확인하세요.';

const COMPACT_TEXT =
  'AI가 웹 검색 결과로 자동 작성한 요약입니다. 틀리거나 오래된 내용이 있을 수 있으니 공식 출처에서 확인하세요.';

export default function AiNotice({ compact = false }: { compact?: boolean }) {
  // On the 이용 안내 page itself the link would only point back at the page.
  const onAbout = useLocation().pathname === '/about';
  return (
    <aside className="ai-notice" data-compact={compact} aria-label="AI 생성 콘텐츠 안내">
      <ShieldAlert size={compact ? 16 : 20} aria-hidden="true" />
      <div>
        <strong className="ai-notice-title">AI 생성 콘텐츠 · 참고용</strong>
        <p>
          {compact ? COMPACT_TEXT : AI_NOTICE_TEXT}
          {!onAbout && (
            <>
              {' '}
              <Link to="/about">이용 안내</Link>
            </>
          )}
        </p>
      </div>
    </aside>
  );
}
