import type { ReactNode } from 'react';
import { AlertTriangle, Inbox, RotateCw } from 'lucide-react';

export function Spinner({ small = false, label }: { small?: boolean; label?: string }) {
  return (
    <>
      <div className={small ? 'spinner spinner-sm' : 'spinner'} aria-hidden="true" />
      {label && <span className="visually-hidden">{label}</span>}
    </>
  );
}

/** Centered "loading…" panel, announced politely to screen readers. */
export function LoadingState({ message = '불러오는 중...' }: { message?: string }) {
  return (
    <div className="state-block" role="status" aria-live="polite">
      <Spinner />
      <span>{message}</span>
    </div>
  );
}

/** Error panel with a retry affordance, instead of a silent console.error. */
export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="state-block" role="alert">
      <AlertTriangle size={28} color="var(--danger-color)" aria-hidden="true" />
      <strong>데이터를 불러오지 못했습니다</strong>
      <span>{message}</span>
      {onRetry && (
        <button type="button" className="btn btn-secondary btn-sm" onClick={onRetry}>
          <RotateCw size={16} aria-hidden="true" />
          다시 시도
        </button>
      )}
    </div>
  );
}

/** Explains why a list is empty rather than rendering nothing at all. */
export function EmptyState({ title, hint, icon }: { title: string; hint?: string; icon?: ReactNode }) {
  return (
    <div className="state-block">
      {icon ?? <Inbox size={28} aria-hidden="true" />}
      <strong>{title}</strong>
      {hint && <span>{hint}</span>}
    </div>
  );
}
