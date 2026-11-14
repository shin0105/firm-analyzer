import axios from 'axios';
import { api, apiUrl, STATIC_SITE } from './api';
import type {
  FirmDetail,
  FirmListItem,
  FirmListResponse,
  FirmQuery,
  ResultsSummaryResponse,
  Taxonomy,
} from './types';

/**
 * The read-only data the viewer pages show. With Flask it comes from `/api`.
 * In the static build it comes from the snapshot `firm-export-site` writes
 * (`src/firm_analyzer/web/static_site.py`), and firm search runs here in the
 * browser instead of on the server.
 */

const DATA = `${import.meta.env.BASE_URL}data`;

/** The firms CSV, with segmentation columns and an AI-generated label per row. */
export const exportCsvUrl = STATIC_SITE ? `${DATA}/firms_export.csv` : apiUrl('/api/export.csv');

/** The Kakao map page, embedded by the 기업 검색 결과 page. */
export const mapUrl = STATIC_SITE ? `${import.meta.env.BASE_URL}map/index.html` : apiUrl('/map');

/** A `data/firms.json` row: an `/api/firms` row plus what the browser needs to search. */
interface SnapshotFirm extends Omit<FirmListItem, 'snippet'> {
  /** File name of the firm's detail, `data/firms/<id>.json`. */
  id: string;
  /** The summary prose, flattened: what search matches and snippets come from. */
  text: string;
}

interface IndexedFirm {
  firm: SnapshotFirm;
  nameKey: string;
  /** Name, address and prose, lower-cased once at load. */
  searchKey: string;
}

let snapshotIndex: Promise<IndexedFirm[]> | null = null;

/** `data/firms.json`, fetched once and shared by search and detail lookups. */
function loadIndex(): Promise<IndexedFirm[]> {
  snapshotIndex ??= axios
    .get<{ firms: SnapshotFirm[] }>(`${DATA}/firms.json`)
    .then((res) =>
      res.data.firms.map((firm) => ({
        firm,
        nameKey: firm.name.toLowerCase(),
        searchKey: `${firm.name}\n${firm.address}\n${firm.text}`.toLowerCase(),
      })),
    )
    .catch((err: unknown) => {
      snapshotIndex = null; // let a retry fetch it again
      throw err;
    });
  return snapshotIndex;
}

/** About `width` characters of `text`, centred on `needle`: `results.snippet` in Python. */
function snippet(text: string, needle: string, width = 90): string {
  const position = needle ? text.toLowerCase().indexOf(needle.toLowerCase()) : -1;
  const start =
    position < 0 || text.length <= width
      ? 0
      : Math.max(0, Math.min(position - Math.floor(width / 3), text.length - width));
  const end = start + width;
  let out = text.slice(start, end).trim();
  if (start > 0) out = `…${out}`;
  if (end < text.length) out += '…';
  return out;
}

/** The segmentation filters of `/api/firms`, applied to a snapshot row. */
function matchesFilters(firm: SnapshotFirm, query: FirmQuery): boolean {
  if (query.segmented && firm.segmented !== (query.segmented === 'true')) return false;
  if (query.sector && firm.sector !== query.sector) return false;
  if (query.vertical && !firm.verticals.includes(query.vertical)) return false;
  if (query.business_model && firm.business_model !== query.business_model) return false;
  if (query.confidence && firm.sector_confidence !== query.confidence) return false;
  return true;
}

/**
 * `/api/firms` over the snapshot. One difference: the server also matches the
 * summary's header and source list, while this matches name, address and prose.
 */
async function searchSnapshot(query: FirmQuery): Promise<FirmListResponse> {
  const all = await loadIndex();
  const scoped = query.category ? all.filter(({ firm }) => firm.category_id === query.category) : all;
  const term = (query.q ?? '').trim();
  const needle = term.toLowerCase();

  const hits: { entry: IndexedFirm; nameMatch: boolean }[] = [];
  for (const entry of scoped) {
    if (!matchesFilters(entry.firm, query)) continue;
    const nameMatch = needle !== '' && entry.nameKey.includes(needle);
    if (needle && !nameMatch && !entry.searchKey.includes(needle)) continue;
    hits.push({ entry, nameMatch });
  }
  // The index is in name order and sort is stable, so this only moves name
  // matches to the front, as the server does.
  hits.sort((a, b) => Number(b.nameMatch) - Number(a.nameMatch));

  const firms: FirmListItem[] = hits.map(({ entry: { firm } }) => ({
    ...firm,
    snippet: snippet(firm.text, term),
  }));
  return { firms, count: firms.length, total: scoped.length };
}

/** Firm counts per category, plus `total`. */
export async function getResultsSummary(): Promise<ResultsSummaryResponse> {
  if (STATIC_SITE) {
    return (await axios.get<ResultsSummaryResponse>(`${DATA}/results-summary.json`)).data;
  }
  return (await api.get<ResultsSummaryResponse>('/api/results/summary')).data;
}

/** The segmentation taxonomy, for filter options and labels. */
export async function getTaxonomy(): Promise<Taxonomy> {
  if (STATIC_SITE) return (await axios.get<Taxonomy>(`${DATA}/taxonomy.json`)).data;
  return (await api.get<Taxonomy>('/api/taxonomy')).data;
}

/** Firms matching a search and filters, without full summaries. */
export async function searchFirms(query: FirmQuery): Promise<FirmListResponse> {
  if (STATIC_SITE) return searchSnapshot(query);
  return (await api.get<FirmListResponse>('/api/firms', { params: query })).data;
}

/** One firm's full summary and segmentation. */
export async function getFirmDetail(categoryId: string, name: string): Promise<FirmDetail> {
  if (STATIC_SITE) {
    const entry = (await loadIndex()).find(
      ({ firm }) => firm.category_id === categoryId && firm.name === name,
    );
    if (!entry) throw new Error('기업을 찾을 수 없습니다.');
    return (await axios.get<FirmDetail>(`${DATA}/firms/${entry.firm.id}.json`)).data;
  }
  const path = `/api/firms/${encodeURIComponent(categoryId)}/${encodeURIComponent(name)}`;
  return (await api.get<FirmDetail>(path)).data;
}
