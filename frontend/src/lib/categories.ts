import type { CategorySummary } from './types';

interface CategoryLook {
  label: string;
  /** A colour token: the three specialised categories carry colour, 일반 stays gray. */
  tone: string;
  note?: string;
  order: number;
}

/**
 * How the coarse `config.yml` categories read in the UI. Ids not listed here
 * keep their config name and colour and sort before 일반.
 */
const LOOKS: Record<string, CategoryLook> = {
  ai_ml: { label: 'AI·머신러닝', tone: 'var(--color-cat-ai)', order: 0 },
  healthcare: { label: '바이오·헬스케어', tone: 'var(--color-cat-bio)', order: 1 },
  finance: { label: '금융·퀀트', tone: 'var(--color-cat-fin)', order: 2 },
  general: {
    label: '일반',
    tone: 'var(--color-cat-gen)',
    note: '특정 분야로 묶이지 않은 업체',
    order: 99,
  },
};

export interface CategoryView extends CategorySummary {
  label: string;
  tone: string;
  note?: string;
}

export function categoryLabel(id: string, fallback?: string): string {
  return LOOKS[id]?.label ?? fallback ?? id;
}

export function categoryTone(id: string, fallback = 'var(--color-faint)'): string {
  return LOOKS[id]?.tone ?? fallback;
}

/** Categories with their UI label and colour, specialised ones first and 일반 last. */
export function categoryViews(categories: CategorySummary[]): CategoryView[] {
  return categories
    .map((category, index) => ({
      view: {
        ...category,
        label: categoryLabel(category.id, category.name),
        tone: categoryTone(category.id, category.color),
        note: LOOKS[category.id]?.note,
      },
      order: LOOKS[category.id]?.order ?? 50 + index,
    }))
    .sort((a, b) => a.order - b.order)
    .map(({ view }) => view);
}
