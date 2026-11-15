/** Join class names, skipping falsy ones. */
export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(' ');
}

export function formatCount(value: number): string {
  return value.toLocaleString('ko-KR');
}

/** `part` as a share of `whole`, one decimal: "10.1%". */
export function formatShare(part: number, whole: number): string {
  return whole > 0 ? `${((part / whole) * 100).toFixed(1)}%` : '0%';
}

const PROVINCE_SHORT: Record<string, string> = {
  서울특별시: '서울',
  부산광역시: '부산',
  대구광역시: '대구',
  인천광역시: '인천',
  광주광역시: '광주',
  대전광역시: '대전',
  울산광역시: '울산',
  세종특별자치시: '세종',
  경기도: '경기',
  강원도: '강원',
  강원특별자치도: '강원',
  충청북도: '충북',
  충청남도: '충남',
  전라북도: '전북',
  전북특별자치도: '전북',
  전라남도: '전남',
  경상북도: '경북',
  경상남도: '경남',
  제주특별자치도: '제주',
};

/** "서울특별시 강남구 봉은사로" → "서울 강남구": enough to place a firm at a glance. */
export function shortPlace(address: string): string {
  const [first, second] = address.trim().split(/\s+/);
  if (!first) return '';
  const province = PROVINCE_SHORT[first] ?? first;
  return second && /[시군구]$/.test(second) ? `${province} ${second}` : province;
}

/**
 * A round axis for a bar chart whose longest bar is `max`: the domain the bars
 * are scaled to, and tick values that never run past `max`.
 */
export function niceAxis(max: number): { domain: number; ticks: number[] } {
  if (max <= 0) return { domain: 1, ticks: [0] };
  const magnitude = 10 ** Math.floor(Math.log10(max / 4));
  let step = magnitude;
  for (const factor of [1, 2, 2.5, 5, 10]) {
    step = factor * magnitude;
    if (max / step <= 5) break;
  }
  const ticks: number[] = [];
  for (let value = 0; value <= max; value += step) ticks.push(value);
  return { domain: Math.ceil(max / step) * step, ticks };
}
