/**
 * 盖法定义：对齐桌面「印章识别」项目 + 需求文档 4.5.2
 * 知章(蓝方) / 行章(黄圆) / 知行对章；基础当量见 membership 阶位规则
 */

export interface SealMethodDef {
  id: number
  name: string
  /** know | guide | improve | do | combo */
  kind: 'know' | 'guide' | 'improve' | 'do' | 'combo'
  stampType: 'know' | 'do' | 'combo'
  zhi: number
  xing: number
  /** 计入报告的当量（引导章不计分） */
  valueNum: number
  valueUnit: 'ZE' | 'XE' | 'DE' | 'Y' | 'G'
  supportsCorners: boolean
  description: string
}

/** 基础：1ZE=10ZZE，1XE=100ZZE，1DE=500ZZE（与需求 6.1 一致，K=10） */
const ZE = 10
const XE = 100
const DE = 500

export const SEAL_METHODS: SealMethodDef[] = [
  {
    id: 1,
    name: '正向章（知章）',
    kind: 'know',
    stampType: 'know',
    zhi: 1,
    xing: 0,
    valueNum: 1 * ZE,
    valueUnit: 'ZE',
    supportsCorners: true,
    description: '单枚蓝色方章正向，ZE=1',
  },
  {
    id: 2,
    name: '引导章（知章）',
    kind: 'guide',
    stampType: 'know',
    zhi: 1,
    xing: 0,
    valueNum: 0,
    valueUnit: 'Y',
    supportsCorners: true,
    description: '知章倒盖 180°，不计当量',
  },
  {
    id: 3,
    name: '改进章（知章）',
    kind: 'improve',
    stampType: 'know',
    zhi: 2,
    xing: 0,
    valueNum: 2 * ZE,
    valueUnit: 'G',
    supportsCorners: true,
    description: '引导后叠正向，1G 计 2ZE',
  },
  {
    id: 4,
    name: '知章二叠章',
    kind: 'know',
    stampType: 'know',
    zhi: 2,
    xing: 0,
    valueNum: 2 * ZE,
    valueUnit: 'ZE',
    supportsCorners: true,
    description: '两枚知章叠盖，ZE=2',
  },
  {
    id: 5,
    name: '知章三叠章',
    kind: 'know',
    stampType: 'know',
    zhi: 3,
    xing: 0,
    valueNum: 3 * ZE,
    valueUnit: 'ZE',
    supportsCorners: true,
    description: '三枚知章品字叠盖，ZE=3',
  },
  {
    id: 6,
    name: '行章',
    kind: 'do',
    stampType: 'do',
    zhi: 0,
    xing: 1,
    valueNum: 1 * XE,
    valueUnit: 'XE',
    supportsCorners: false,
    description: '单枚黄色圆章，XE=1',
  },
  {
    id: 7,
    name: '行章二叠章',
    kind: 'do',
    stampType: 'do',
    zhi: 0,
    xing: 2,
    valueNum: 2 * XE,
    valueUnit: 'XE',
    supportsCorners: false,
    description: '两枚行章叠盖，XE=2',
  },
  {
    id: 8,
    name: '行章三叠章',
    kind: 'do',
    stampType: 'do',
    zhi: 0,
    xing: 3,
    valueNum: 3 * XE,
    valueUnit: 'XE',
    supportsCorners: false,
    description: '三枚行章品字叠盖，XE=3',
  },
  {
    id: 9,
    name: '知行对章',
    kind: 'combo',
    stampType: 'combo',
    zhi: 1,
    xing: 1,
    valueNum: 1 * DE,
    valueUnit: 'DE',
    supportsCorners: true,
    description: '蓝黄叠盖 50%，DE=1',
  },
  {
    id: 10,
    name: '知行对章二叠章',
    kind: 'combo',
    stampType: 'combo',
    zhi: 2,
    xing: 2,
    valueNum: 2 * DE,
    valueUnit: 'DE',
    supportsCorners: true,
    description: '知行对章二叠，DE=2',
  },
  {
    id: 11,
    name: '知行对章三叠章',
    kind: 'combo',
    stampType: 'combo',
    zhi: 3,
    xing: 3,
    valueNum: 3 * DE,
    valueUnit: 'DE',
    supportsCorners: true,
    description: '知行对章三叠，DE=3',
  },
]

export function sealMethodById(id: number): SealMethodDef | undefined {
  return SEAL_METHODS.find((m) => m.id === id)
}

export function formatSealValue(m: SealMethodDef): string {
  if (m.valueUnit === 'Y') return '引导章 · 不计当量'
  // 改进章归入知章单位（2ZE），其余按各自单位显示
  const unit = m.valueUnit === 'G' ? 'ZE' : m.valueUnit
  return `+${Math.round(m.valueNum / UNIT_BASE[unit])} ${unit}`
}

/** 各单位的 ZZE 基数：1ZE=10、1XE=100、1DE=500 */
export const UNIT_BASE: Record<'ZE' | 'XE' | 'DE', number> = { ZE, XE, DE }

/** 记录类型 → 当量单位：知行对章=DE、行章=XE、知章=ZE */
export function unitOfStampType(t?: string): 'ZE' | 'XE' | 'DE' {
  if (t === 'combo') return 'DE'
  if (t === 'do') return 'XE'
  return 'ZE'
}

/**
 * 列表里的当量文案，统一成「+130 DE / +110 ZE / +110 XE」这一种写法。
 * 不再输出“XX当量（XE）”这类中文注解，单位即说明。
 */
export function formatStampValue(valueNum: number, stampType?: string): string {
  const unit = unitOfStampType(stampType)
  return `+${Math.round((Number(valueNum) || 0) / UNIT_BASE[unit])} ${unit}`
}
