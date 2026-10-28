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
  if (m.valueUnit === 'G') return `+${m.valueNum} ZZE（改进章 2ZE）`
  const unit =
    m.valueUnit === 'ZE' ? '知章' : m.valueUnit === 'XE' ? '行章' : '对章'
  return `+${m.valueNum} ZZE（${unit}）`
}
