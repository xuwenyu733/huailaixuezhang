<template>
  <view class="page">
    <view class="toggle">
      <text class="t" :class="{ on: tab === 'family' }" @click="tab = 'family'">家庭端编码</text>
      <text class="t" :class="{ on: tab === 'school' }" @click="tab = 'school'">学校端编码</text>
    </view>

    <view v-if="tab === 'family'">
      <view class="card" v-for="b in familyBlocks" :key="b.title">
        <text class="bt" :style="{ color: b.color }">{{ b.title }}</text>
        <text class="bd">{{ b.desc }}</text>
      </view>
      <view class="card">
        <text class="title">分学段规则</text>
        <view class="rule" v-for="r in stageRules" :key="r.h">
          <text class="rh">{{ r.h }}</text>
          <text class="rd">{{ r.d }}</text>
        </view>
      </view>
    </view>

    <view v-else>
      <view class="card">
        <view class="thead">
          <text>维度</text><text>编码</text><text>观测点</text><text>章型</text>
        </view>
        <view class="tr" v-for="row in schoolRows" :key="row.code">
          <text>{{ row.dim }}</text>
          <text>{{ row.code }}</text>
          <text>{{ row.point }}</text>
          <text>{{ row.type }}</text>
        </view>
      </view>
      <view class="card">
        <text class="title">使用说明</text>
        <text class="li" v-for="(t, i) in tips" :key="i">• {{ t }}</text>
      </view>
      <view class="card">
        <text class="title">印章样式说明</text>
        <view class="styles">
          <view class="st"><view class="stamp-square" /><text>知章 带角几何</text></view>
          <view class="st"><view class="stamp-round" /><text>行章 圆形轮廓</text></view>
          <view class="st"><view class="stamp-combo"><view class="sq" /><view class="rd" /></view><text>知行对章</text></view>
        </view>
        <text class="bd">中心溯源区承载学科分类，周边编码区承载维度信息</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const tab = ref<'family' | 'school'>('family')
const familyBlocks = [
  { title: '蓝章 · 学生自评', color: '#2563eb', desc: '三年级起逐步开放，学生对自身当日表现进行评价盖章，家长拥有审核收回权。' },
  { title: '黄章 · 家长认证', color: '#f59e0b', desc: '家长对家庭表现、重大进步、荣誉奖励进行补充盖章，可申请知行对章认证。' },
  { title: '知行对章 · 共同认证', color: '#10b981', desc: '重大荣誉与成果，由家长与孩子共同盖章确认，获得最高当量加成。' },
]
const stageRules = [
  { h: '小学低段', d: '家长全权盖章，学生仅参与不操作' },
  { h: '小学高段', d: '学生盖蓝章自评，家长盖黄章认证' },
  { h: '初中及以上', d: '学生自主盖章为主，家长保留收回权' },
]
const schoolRows = [
  { dim: '智育', code: 'Z01', point: '课堂主动发言', type: '知章' },
  { dim: '智育', code: 'Z02', point: '作业高质量完成', type: '知章' },
  { dim: '智育', code: 'X01', point: '单元测试达标', type: '行章' },
  { dim: '德育', code: 'D01', point: '遵守纪律', type: '知章' },
  { dim: '德育', code: 'ZX01', point: '志愿服务完成', type: '知行对章' },
  { dim: '体育', code: 'T01', point: '课间操达标', type: '知章' },
]
const tips = [
  '印章自带教师编号，便于溯源追责',
  '支持3-7天周期表轮转，避免频繁换本',
  '可按班级整表采集，批量识别上传',
  '支持异常印章人工复核与修正',
]
</script>

<style scoped>
.page { min-height: 100vh; background: #f9fafb; padding: 24rpx; }
.toggle { display: flex; background: #fff; border-radius: 14rpx; padding: 6rpx; margin-bottom: 20rpx; }
.t { flex: 1; text-align: center; padding: 16rpx; font-size: 26rpx; color: #6b7280; border-radius: 10rpx; }
.t.on { background: #2563eb; color: #fff; }
.card { background: #fff; border-radius: 20rpx; padding: 28rpx; margin-bottom: 16rpx; }
.bt { display: block; font-size: 30rpx; font-weight: 700; margin-bottom: 10rpx; }
.bd { display: block; font-size: 24rpx; color: #6b7280; line-height: 1.7; }
.title { display: block; font-size: 30rpx; font-weight: 600; margin-bottom: 16rpx; }
.rule { margin-bottom: 16rpx; }
.rh { display: block; font-size: 26rpx; font-weight: 600; color: #111827; }
.rd { display: block; font-size: 24rpx; color: #6b7280; margin-top: 6rpx; }
.thead, .tr { display: grid; grid-template-columns: 1fr 1.2fr 2fr 1.2fr; gap: 8rpx; font-size: 22rpx; padding: 14rpx 0; }
.thead { color: #9ca3af; border-bottom: 2rpx solid #f3f4f6; }
.tr { border-bottom: 2rpx solid #f9fafb; color: #374151; }
.li { display: block; font-size: 24rpx; color: #6b7280; line-height: 1.8; }
.styles { display: flex; justify-content: space-around; margin: 20rpx 0; }
.st { display: flex; flex-direction: column; align-items: center; gap: 12rpx; font-size: 22rpx; color: #6b7280; }
</style>
