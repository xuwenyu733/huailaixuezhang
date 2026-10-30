import { addChild, getCurrentChild, listChildrenByClassCode } from './childRepo'
import { listStampsByChild, listStampsByOwner, saveStamp } from './stampRepo'
import { DIMENSIONS, dimNameOf } from '@/constants/dimensions'
import type { StampRow } from '@/types/user'

export type ReportMode = 'month' | 'term' | 'dim'

export interface ReportBundle {
  months: string[]
  growth: number[]
  rate: number[]
  fusion: { knowStrong: number; doStrong: number; balance: number }
  dims: { name: string; me: number; norm?: number }[]
  advice: string
  totalZze: number
  ranks: { av: string; name: string; zze: string; me: boolean }[]
}

/**
 * 旧版本按「德育/智育…」手填维度，现已改为按编码第 1 位归类，此映射不再使用。
 * 保留注释是为了说明历史数据的口径差异：老记录若没有合法编码，不计入维度画像。
 */

function monthKey(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '未知'
  return `${d.getMonth() + 1}月`
}

/** 排序用：2026-05 */
function monthSortKey(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '0000-00'
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  return `${y}-${m}`
}

function inRecentMonths(iso: string, monthsBack: number): boolean {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return false
  const start = new Date()
  start.setMonth(start.getMonth() - monthsBack)
  start.setDate(1)
  start.setHours(0, 0, 0, 0)
  return d.getTime() >= start.getTime()
}

function filterByMode(rows: StampRow[], mode: ReportMode): StampRow[] {
  // 月度：近 6 个月按月粒度；学期：近 6 个月；维度：全部
  if (mode === 'month') return rows.filter((r) => inRecentMonths(r.created_at || '', 6))
  if (mode === 'term') return rows.filter((r) => inRecentMonths(r.created_at || '', 6))
  return rows
}

async function buildClassRanks(
  ownerId: string | number,
  childName: string | undefined,
  myZze: number,
): Promise<ReportBundle['ranks']> {
  const meName = childName ? `${childName}（我）` : '我'
  const me = {
    av: (childName || '我').slice(0, 1),
    name: meName,
    zze: String(myZze),
    me: true,
  }
  try {
    const child = await getCurrentChild(ownerId)
    const classCode = child?.class_code?.trim()
    if (!classCode) return [me]

    const classmates = await listChildrenByClassCode(classCode)
    const ranks: ReportBundle['ranks'] = []
    for (const c of classmates.slice(0, 30)) {
      const stamps = await listStampsByChild(c.Id, 200)
      const zze = stamps.reduce((sum, s) => sum + (Number(s.value_num) || 0), 0)
      const isMe = String(c.parent_id) === String(ownerId) && (!childName || c.name === childName)
      ranks.push({
        av: c.avatar_text || c.name.slice(0, 1),
        name: isMe ? `${c.name}（我）` : c.name,
        zze: String(zze),
        me: isMe,
      })
    }
    ranks.sort((a, b) => Number(b.zze) - Number(a.zze))
    if (!ranks.some((r) => r.me)) ranks.unshift(me)
    return ranks.slice(0, 10)
  } catch {
    return [me]
  }
}

export async function buildParentReport(
  ownerId: string | number,
  childName?: string,
  mode: ReportMode = 'month',
): Promise<ReportBundle> {
  let rows = await listStampsByOwner(ownerId, 300)
  if (childName) {
    rows = rows.filter((r) => !r.child_name || r.child_name === childName)
  }
  rows = filterByMode(rows, mode)

  const monthSum: Record<string, number> = {}
  const monthLabel: Record<string, string> = {}
  const dimSum: Record<string, number> = {}
  let know = 0
  let doAct = 0
  let combo = 0
  let physical = 0
  let totalZze = 0

  rows.forEach((r: StampRow) => {
    const sk = monthSortKey(r.created_at || '')
    const m = monthKey(r.created_at || '')
    if (!monthSum[sk]) {
      monthSum[sk] = 0
      monthLabel[sk] = m
    }
    const v = Number(r.value_num) || 0
    monthSum[sk] += v
    totalZze += v
    if (r.stamp_type === 'combo') combo += 1
    else if (r.stamp_type === 'do') doAct += 1
    else know += 1
    if (r.source === 'physical') physical += 1
    // 维度不再看手填字段，一律按编码第 1 位归类；旧数据没有合法编码时不计维度
    const dimName = dimNameOf(String(r.code_text || '').replace(/\D/g, '').charAt(0))
    if (dimName) dimSum[dimName] = (dimSum[dimName] || 0) + v
  })

  const sortedKeys = Object.keys(monthSum).sort()
  const keys = sortedKeys.slice(-6)
  const months = keys.map((k) => monthLabel[k] || k)
  let acc = 0
  const growth = keys.map((k) => {
    acc += monthSum[k] || 0
    return acc
  })
  const rate = keys.map((k) => monthSum[k] || 0)

  const totalActs = Math.max(1, know + doAct + combo)
  const knowStrong = Math.round((know / totalActs) * 100)
  const doStrong = Math.round((doAct / totalActs) * 100)
  const balance = Math.max(0, 100 - knowStrong - doStrong)

  const dimNames = DIMENSIONS.map((d) => d.name)
  const maxDim = Math.max(1, ...Object.values(dimSum), 1)
  let dims = dimNames.map((name) => ({
    name,
    me: Math.min(99, Math.round(((dimSum[name] || 0) / maxDim) * 90) || (dimSum[name] ? 40 : 15)),
  }))
  if (mode === 'dim') {
    dims = [...dims].sort((a, b) => b.me - a.me)
  }

  let advice =
    '暂无足够盖章数据。请先完成虚拟盖章或实体采集，再查看成长分析。'
  if (rows.length) {
    if (mode === 'dim') {
      const top = dims[0]
      advice = `本周期维度专项：${top.name}相对最强（指数 ${top.me}）。可对照较弱维度安排针对性任务。`
    } else if (knowStrong >= 60) {
      advice =
        '该生认知积累扎实，课堂相关知章较多，实践转化（知行对章）仍有提升空间。建议增加应用类任务，促进知行融合。'
    } else if (balance >= 30) {
      advice =
        '知行对章占比良好，说明过程与成果衔接较好。可继续保持并在薄弱维度定向补强。'
    } else {
      advice =
        '盖章分布较分散。建议围绕核心维度持续积累，形成稳定成长曲线。'
    }
    if (physical > 0) {
      advice += ` 本期实体采集 ${physical} 次。`
    }
  }

  const ranks = await buildClassRanks(ownerId, childName, totalZze)

  return {
    months: months.length ? months : [mode === 'month' ? '本月' : '本期'],
    growth: growth.length ? growth : [0],
    rate: rate.length ? rate : [0],
    fusion: { knowStrong, doStrong, balance },
    dims,
    advice,
    totalZze,
    ranks,
  }
}

const FAKE_DIMS = [
  { primary: '智育', secondary: '课堂参与', subject: '语文' },
  { primary: '德育', secondary: '志愿服务', subject: '德育' },
  { primary: '体育', secondary: '体能达标', subject: '体育' },
  { primary: '美育', secondary: '艺术表现', subject: '美术' },
  { primary: '劳育', secondary: '劳动实践', subject: '综合' },
  { primary: '品格', secondary: '诚实守信', subject: '德育' },
]

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms))
}

/** 近 6 个月每月造几条虚假盖章，写入 PMIS，供报告页出图 */
export async function seedFakeReportData(ownerId: string | number): Promise<{
  childName: string
  count: number
}> {
  if (String(ownerId).startsWith('demo_')) {
    throw new Error('演示账号不入库，请用手机号登录正式家长账号')
  }

  let child = await getCurrentChild(ownerId)
  if (!child) {
    const card = `HLXZ${Date.now().toString().slice(-8)}`
    try {
      child = await addChild({
        parentId: ownerId,
        name: '测试同学',
        school: '淮安实验小学',
        className: '三年二班',
        classCode: 'HA302',
        cardNo: card,
        studentNo: `S${card.slice(-6)}`,
      })
    } catch (e: any) {
      throw new Error(e?.message || '创建测试孩子失败')
    }
  }

  // 每月增量当量（对齐 demo 曲线量级）
  const monthAdds = [200, 180, 170, 170, 230, 330]
  let count = 0
  const now = new Date()
  const errors: string[] = []

  for (let back = 5; back >= 0; back--) {
    const base = new Date(now.getFullYear(), now.getMonth() - back, 1)
    const add = monthAdds[5 - back]
    const pieces = back % 2 === 0 ? 3 : 2
    const each = Math.max(10, Math.round(add / pieces))
    for (let i = 0; i < pieces; i++) {
      const dim = FAKE_DIMS[(back + i) % FAKE_DIMS.length]
      const isCombo = i === pieces - 1 && back <= 2
      const stampType = isCombo ? 'combo' : i === 0 ? 'do' : 'know'
      const valueNum = isCombo ? each + 20 : each
      const day = new Date(
        base.getFullYear(),
        base.getMonth(),
        Math.min(28, 5 + i * 7),
        10 + i,
        20,
        0,
      )
      try {
        await saveStamp({
          ownerId,
          ownerRole: 'parent',
          childId: child.Id,
          childName: child.name,
          cardNo: child.card_no,
          source: i === 0 ? 'physical' : 'virtual',
          stampType,
          knowKind: stampType === 'know' ? '正向章' : '',
          stackKind: '无',
          subject: dim.subject,
          primaryDim: dim.primary,
          secondaryDim: dim.secondary,
          codeTl: 1,
          codeTr: 2,
          codeBl: 3,
          codeBr: (back + i) % 10,
          codeText: `123${(back + i) % 10}`,
          valueText: isCombo
            ? `+${valueNum} DE`
            : stampType === 'do'
              ? `+${valueNum} XE`
              : `+${valueNum} ZE`,
          valueNum,
          teacherName: '李老师',
          teacherStampNo: 'T9901',
          note: '虚假演示数据',
          status: 'confirmed',
          createdAt: day.toISOString(),
        })
        count += 1
        await sleep(80)
      } catch (e: any) {
        errors.push(e?.message || '写入失败')
      }
    }
  }

  if (count === 0) {
    throw new Error(errors[0] || '盖章数据写入失败，请检查网络/PMIS')
  }

  return { childName: child.name, count }
}
