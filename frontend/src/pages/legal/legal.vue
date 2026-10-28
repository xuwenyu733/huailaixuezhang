<template>
  <view class="page">
    <text class="h">{{ title }}</text>
    <text class="p" v-for="(p, i) in paragraphs" :key="i">{{ p }}</text>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'

const kind = ref('agreement')

const title = computed(() => (kind.value === 'privacy' ? '隐私政策' : '用户协议'))

const paragraphs = computed(() =>
  kind.value === 'privacy'
    ? [
        '淮来学长（下称“本应用”）仅收集完成家长注册、登录、推荐、盖章与会员所必需的信息。',
        '我们会保存手机号、姓名、密码、推荐关系、孩子档案、盖章记录、订单与消息。密码用于登录校验，页面展示时对手机号做脱敏。',
        '数据存放在项目指定的 PMIS 数据表中，不用于与本业务无关的营销。',
        '你可在设置中关闭部分通知，或退出登录。删除孩子为软删除，历史盖章记录仍保留以便报告追溯。',
        '如需更正个人信息，请在「个人资料」中修改姓名；修改密码后需重新登录。',
      ]
    : [
        '欢迎使用淮来学长家长端。注册或登录即表示你同意本协议。',
        '家长账号由本人注册。教师账号由学校在教师管理中分配，默认初始密码须尽快修改。',
        '推荐码仅用于建立推荐关系。被推荐人开通会员后，推荐人按规则获得积分，积分可抵扣年费。',
        '盖章数据用于成长评价报告。实体章识别在未配置云端密钥时使用模拟结果，确认上传前你可以修改字段。',
        '商城周边通过本应用登记购买意向并写入订单；第三方店铺成交不自动回写物流。',
        '请勿借用他人账号，勿泄露密码与推荐码。',
      ],
)

onLoad((q) => {
  kind.value = String(q?.type || 'agreement')
  uni.setNavigationBarTitle({ title: kind.value === 'privacy' ? '隐私政策' : '用户协议' })
})
</script>

<style scoped>
.page { min-height: 100vh; background: #fff; padding: 32rpx 36rpx 80rpx; }
.h { display: block; font-size: 36rpx; font-weight: 700; margin-bottom: 24rpx; }
.p { display: block; font-size: 28rpx; color: #374151; line-height: 1.8; margin-bottom: 20rpx; }
</style>
