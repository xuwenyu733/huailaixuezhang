/**
 * 七大维度（编码第 1 位）。
 *
 * 依据《知行对章盖印通用技术标准》第六部分：格物、致知、诚意、正心、体育、美育、劳育，编号 1–7。
 * 评价维度不再由用户手选，一律由编码推导：编码第 1 位 = 维度编号。
 * 若后续要改维度口径，只改这一个文件，前端其余位置都从这里取名。
 */

export interface DimEntry {
  code: number
  name: string
}

export const DIMENSIONS: DimEntry[] = [
  { code: 1, name: '格物' },
  { code: 2, name: '致知' },
  { code: 3, name: '诚意' },
  { code: 4, name: '正心' },
  { code: 5, name: '体育' },
  { code: 6, name: '美育' },
  { code: 7, name: '劳育' },
]

export const DIM_NAME_BY_CODE: Record<number, string> = DIMENSIONS.reduce(
  (acc, d) => {
    acc[d.code] = d.name
    return acc
  },
  {} as Record<number, string>,
)

/** 编码第 1 位是否合法（1–7） */
export function isDimCode(n: number | string): boolean {
  return Boolean(DIM_NAME_BY_CODE[Number(n)])
}

/** 由编码第 1 位取维度名，非法返回空串 */
export function dimNameOf(code: number | string): string {
  return DIM_NAME_BY_CODE[Number(code)] || ''
}

export interface CodeParts {
  /** 主线三位，如 1-1-1 */
  line: string
  /** 个性化位（右下），无则 0 */
  personal: number
  tl: number
  tr: number
  bl: number
  br: number
}

/** 把 1110 / 1-1-1-0 / 111 统一拆成四角 */
export function splitCode(codeText: string | number): CodeParts {
  const digits = String(codeText ?? '')
    .replace(/[^\d]/g, '')
    .padEnd(4, '0')
    .slice(0, 4)
    .split('')
    .map((d) => Number(d))
  const [tl, tr, bl, br] = digits
  return { tl, tr, bl, br, line: `${tl}-${tr}-${bl}`, personal: br }
}
