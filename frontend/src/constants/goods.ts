export interface ShopGoods {
  tag: string
  name: string
  sub: string
  price: string
  bg: string
  kind: 'shop' | 'incentive'
  /** 官网商品页地址；留空则回落到 OFFICIAL_SITE */
  url?: string
}

/**
 * 官网地址。
 *
 * 待确认项（见 docs/待确认清单.md 第 3 条）：域名是否就是这一个、是否要给每件商品
 * 单独的详情页链接。现在全部落到官网首页，改这里一处即可全局生效。
 */
export const OFFICIAL_SITE = 'https://www.wiidu.com.cn'

/** 商品对应的官网地址：优先单品链接，否则官网首页 */
export function officialUrlOf(g?: { url?: string }): string {
  return g?.url || OFFICIAL_SITE
}

export const SHOP_GOODS: ShopGoods[] = [
  { tag: '印油', name: '专用光敏印油', sub: '蓝/黄/红 三色可选', price: '15.00', bg: '#dbeafe', kind: 'shop' },
  { tag: '记录册', name: '成长记录册', sub: '一学期装 · 含编码表', price: '38.00', bg: '#fef3c7', kind: 'shop' },
  { tag: '印章', name: '教师专用印章', sub: '带编号 · 光敏材质', price: '58.00', bg: '#d1fae5', kind: 'shop' },
  { tag: '贴片', name: '智能识别贴片', sub: 'NFC近场通信', price: '2.50', bg: '#ede9fe', kind: 'shop' },
]

export const INCENTIVE_GOODS: ShopGoods[] = [
  { tag: '笔盒', name: '多功能塑料铅笔盒', sub: '蓝/黄/红 三色可选', price: '15.00', bg: '#e0f2fe', kind: 'incentive' },
  { tag: '书', name: '《三体》', sub: '第一章-第三章可选', price: '38.00', bg: '#fce7f3', kind: 'incentive' },
  { tag: '玩偶', name: '某知名IP玩偶', sub: '20cm高度，柔软细致', price: '58.00', bg: '#ffedd5', kind: 'incentive' },
  { tag: '笔', name: '百乐0.5mm圆珠笔', sub: '蓝/黑/红三色可选', price: '5.00', bg: '#ecfccb', kind: 'incentive' },
]

export const SERVICE_PHONE = '4008002026'
