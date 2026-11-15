import axios from 'axios';
import { STATIC_SITE, apiUrl } from './api';

/**
 * The 인원배정 list by 관할 지방병무청, for the 개요 page. It is read from the
 * map's own data file, which `uv run firm-geocode` writes from the active list
 * as `const firmsData = [ …JSON… ];`, so no extra endpoint or export is needed
 * and the browser reuses the download when the map opens.
 */
const FIRMS_DATA_URL = STATIC_SITE
  ? `${import.meta.env.BASE_URL}static/js/firms_data.js`
  : apiUrl('/static/js/firms_data.js');

export interface RegionCount {
  /** The list's own value, e.g. "대전.충남": what the map's `?region=` expects. */
  id: string;
  label: string;
  count: number;
}

export interface RosterRegions {
  total: number;
  /** From the source file name, e.g. "2026_전문연구요원_인원배정.csv". */
  year: string | null;
  /** Largest first. */
  regions: RegionCount[];
}

/** "대전.충남" → "대전/충남", as the map labels it. */
export function regionLabel(region: string): string {
  return region.replace(/\./g, '/');
}

export async function getRosterRegions(): Promise<RosterRegions> {
  const response = await axios.get<string>(FIRMS_DATA_URL, {
    responseType: 'text',
    transformResponse: (body) => body,
  });
  const text = response.data;
  const declaration = /const\s+firmsData\s*=\s*\[/.exec(text);
  const end = text.lastIndexOf(']');
  if (!declaration || end < declaration.index) {
    throw new Error('배정 명단 데이터를 읽지 못했습니다.');
  }
  const start = declaration.index + declaration[0].length - 1;
  const firms = JSON.parse(text.slice(start, end + 1)) as { jurisdiction?: string }[];

  const counts = new Map<string, number>();
  for (const firm of firms) {
    const region = firm.jurisdiction?.trim() || '기타';
    counts.set(region, (counts.get(region) ?? 0) + 1);
  }
  const regions = [...counts]
    .map(([id, count]) => ({ id, label: regionLabel(id), count }))
    .sort((a, b) => b.count - a.count);

  const year = /firmsDataSource\s*=\s*["'](\d{4})/.exec(text)?.[1] ?? null;
  return { total: firms.length, year, regions };
}
