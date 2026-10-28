import { TABLES } from '@/constants/tables'
import type { TeacherRow } from '@/types/user'
import {
  fieldInt,
  fieldVarchar,
  n,
  q,
  queryBySql,
  saveRow,
} from './pmis'

export async function listTeachersBySchool(
  schoolId: string | number,
): Promise<TeacherRow[]> {
  const sql = `
    select * from ${TABLES.teacher}
    where isDel = 0 and school_id = ${n(schoolId)}
    order by Id desc
  `.replace(/\s+/g, ' ').trim()
  return (await queryBySql(sql)) as TeacherRow[]
}

export async function findTeacherByStampNo(
  stampNo: string,
): Promise<TeacherRow | null> {
  const sql = `select * from ${TABLES.teacher} where isDel = 0 and stamp_no = ${q(stampNo)} limit 1`
  const rows = await queryBySql(sql)
  return (rows[0] as TeacherRow) || null
}

export async function addTeacher(payload: {
  schoolId: string | number
  name: string
  jobNo?: string
  jobDesc?: string
  stampNo: string
  phone?: string
  password?: string
}): Promise<TeacherRow> {
  const name = payload.name.trim()
  const stampNo = payload.stampNo.trim()
  if (!name) throw new Error('请填写教师姓名')
  if (!stampNo) throw new Error('请填写印章编号')

  const existed = await findTeacherByStampNo(stampNo)
  if (existed) throw new Error('该印章编号已绑定其他教师')

  const now = new Date().toISOString()
  await saveRow(TABLES.teacher, {
    school_id: fieldInt('学校账号Id', payload.schoolId),
    name: fieldVarchar('教师姓名', name, 50),
    job_no: fieldVarchar('工号', payload.jobNo || '', 40),
    job_desc: fieldVarchar('班级科目', payload.jobDesc || '', 80),
    stamp_no: fieldVarchar('印章编号', stampNo, 40),
    phone: fieldVarchar('电话', payload.phone || '', 20),
    password: fieldVarchar('登录密码', payload.password || '123456a', 100),
    created_at: fieldVarchar('创建时间', now, 40),
  })

  const list = await listTeachersBySchool(payload.schoolId)
  const created = list.find((t) => t.stamp_no === stampNo)
  if (!created) throw new Error('添加成功但读取失败')
  return created
}
