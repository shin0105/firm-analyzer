import { Link, useLocation } from 'react-router-dom';
import { cx } from '../lib/format';

/**
 * The label on every view of AI-written firm content. Same wording as
 * `AI_NOTICE_KO` in `src/firm_analyzer/notice.py`; keep the two in step.
 */
export const AI_NOTICE_TEXT =
  '이 요약은 공개 웹 검색 결과를 바탕으로 AI가 자동 생성한 참고 자료입니다. ' +
  '사실과 다르거나 오래된 정보, 동명의 다른 기업 정보가 섞여 있을 수 있으며, ' +
  '해당 기업의 공식 입장이나 평가가 아닙니다. 지원·투자 등 중요한 결정 전에는 ' +
  '반드시 기업의 공식 채널에서 직접 확인하세요.';

/** The short form, under every firm summary and in the page footer. */
export const AI_NOTICE_SHORT =
  'AI가 웹 검색 결과로 자동 작성한 요약입니다. 틀리거나 오래된 내용이 있을 수 있으니 공식 출처에서 확인하세요.';

/** Red pen: the mark that sits on every AI-written block. */
export function AiTag() {
  return <span className="ai-tag">AI 요약</span>;
}

/** The tag and the short notice on one line. */
export function AiLine({ className }: { className?: string }) {
  // On the 이용 안내 page itself the link would only point back at the page.
  const onAbout = useLocation().pathname === '/about';
  return (
    <p className={cx('flex items-start gap-2 text-[12.5px] leading-relaxed text-ink-2', className)}>
      <AiTag />
      <span>
        {AI_NOTICE_SHORT}
        {!onAbout && (
          <>
            {' '}
            <Link className="link font-medium" to="/about">
              이용 안내
            </Link>
          </>
        )}
      </span>
    </p>
  );
}

/** The full notice, on the 이용 안내 page. */
export default function AiNotice() {
  return (
    <aside
      className="grid gap-2 rounded-[14px] bg-redpen-tint px-5 py-4"
      aria-label="AI 생성 콘텐츠 안내"
    >
      <p className="flex items-center gap-2 text-[15px] font-bold text-redpen">
        <AiTag />
        AI 생성 콘텐츠 · 참고용
      </p>
      <p className="text-[15px] leading-relaxed">{AI_NOTICE_TEXT}</p>
    </aside>
  );
}
