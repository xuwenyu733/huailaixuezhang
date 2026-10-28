import { TABLES } from '@/constants/tables'
import {
  fieldInt,
  fieldVarchar,
  n,
  q,
  queryBySql,
  saveRow,
  updateBySql,
} from './pmis'

export interface GoalRow {
  Id: number | string
  parent_id: number | string
  child_id: number | string
  child_name: string
  title: string
  reward_name: string
  reward_price: string
  target_points: number
  current_points: number
  status: 'active' | 'done' | 'cancel'
  created_at: string
  done_at?: string
}

export async function listGoalsByParent(
  parentId: string | number,
): Promise<GoalRow[]> {
  const sql = `
    select * from ${TABLES.goal}
    where isDel = 0 and parent_id = ${n(parentId)}
    order by Id desc
  `.replace(/\s+/g, ' ').trim()
  return (await queryBySql(sql)) as GoalRow[]
}

export async function createGoal(payload: {
  parentId: string | number
  childId?: string | number
  childName?: string
  title: string
  rewardName: string
  rewardPrice?: string
  targetPoints: number
}): Promise<GoalRow> {
  const title = payload.title.trim()
  const rewardName = payload.rewardName.trim()
  const target = Number(payload.targetPoints) || 0
  if (!title) throw new Error('请填写目标标题')
  if (!rewardName) throw new Error('请填写奖励商品')
  if (target <= 0) throw new Error('目标当量需大于 0')

  const now = new Date().toISOString()
  await saveRow(TABLES.goal, {
    parent_id: fieldInt('家长Id', payload.parentId),
    child_id: fieldInt('孩子Id', payload.childId || 0),
    child_name: fieldVarchar('学生姓名', payload.childName || '', 50),
    title: fieldVarchar('目标标题', title, 80),
    reward_name: fieldVarchar('奖励商品', rewardName, 80),
    reward_price: fieldVarchar('奖励价格', payload.rewardPrice || '', 20),
    target_points: fieldInt('目标当量', target),
    current_points: fieldInt('当前进度', 0),
    status: fieldVarchar('状态', 'active', 20),
    created_at: fieldVarchar('创建时间', now, 40),
    done_at: fieldVarchar('完成时间', '', 40),
  })
  const list = await listGoalsByParent(payload.parentId)
  const created = list.find((g) => g.title === title && g.reward_name === rewardName)
  if (!created) throw new Error('创建成功但读取失败')
  return created
}

export async function addGoalProgress(
  goalId: string | number,
  delta: number,
): Promise<{ done: boolean; goal: GoalRow }> {
  const rows = await queryBySql(
    `select * from ${TABLES.goal} where Id = ${n(goalId)} and isDel = 0 limit 1`,
  )
  const g = rows[0] as GoalRow
  if (!g) throw new Error('目标不存在')
  if (g.status !== 'active') throw new Error('目标已结束')
  const next = Math.max(0, Number(g.current_points) || 0) + Math.max(0, delta)
  const done = next >= Number(g.target_points)
  if (done) {
    const doneAt = new Date().toISOString()
    await updateBySql(`
      update ${TABLES.goal}
      set current_points = ${n(next)},
          status = ${q('done')},
          done_at = ${q(doneAt)}
      where Id = ${n(goalId)} and isDel = 0
    `.replace(/\s+/g, ' ').trim())
    return {
      done: true,
      goal: { ...g, current_points: next, status: 'done', done_at: doneAt },
    }
  }
  await updateBySql(
    `update ${TABLES.goal} set current_points = ${n(next)} where Id = ${n(goalId)} and isDel = 0`,
  )
  return { done: false, goal: { ...g, current_points: next } }
}

/** 盖章后给该孩子进行中的目标累加当量；达成时通知家长 */
export async function bumpActiveGoals(
  parentId: string | number,
  childId: string | number,
  delta: number,
): Promise<void> {
  if (!delta) return
  const list = await listGoalsByParent(parentId)
  const active = list.filter(
    (g) => g.status === 'active' && String(g.child_id) === String(childId),
  )
  const { pushMessage } = await import('./messageRepo')
  for (const g of active) {
    const result = await addGoalProgress(g.Id, delta)
    if (result.done) {
      await pushMessage({
        ownerId: parentId,
        title: '激励目标已达成',
        content: `${result.goal.child_name || '孩子'}完成「${result.goal.title}」，可兑换 ${result.goal.reward_name}`,
        category: 'system',
      })
    }
  }
}

export async function cancelGoal(goalId: string | number): Promise<void> {
  await updateBySql(
    `update ${TABLES.goal} set status = ${q('cancel')} where Id = ${n(goalId)} and isDel = 0`,
  )
}
