<script setup lang="ts">
import { onLaunch, onShow, onHide } from '@dcloudio/uni-app'

/** H5 下相对路径会被拼到当前页目录导致图标 404，启动时强制根路径 */
function fixH5TabBarIcons() {
  // #ifdef H5
  const tabs = [
    ['tab-home', 'tab-home-active'],
    ['tab-scan', 'tab-scan-active'],
    ['tab-report', 'tab-report-active'],
    ['tab-mall', 'tab-mall-active'],
    ['tab-mine', 'tab-mine-active'],
  ] as const
  tabs.forEach(([off, on], index) => {
    try {
      uni.setTabBarItem({
        index,
        iconPath: `/static/${off}.png`,
        selectedIconPath: `/static/${on}.png`,
      })
    } catch (e) {
      console.warn('[tabBar]', e)
    }
  })
  // #endif
}

onLaunch(() => {
  console.log('淮安学长 App Launch')
  fixH5TabBarIcons()
})
onShow(() => {
  console.log('App Show')
  fixH5TabBarIcons()
})
onHide(() => {
  console.log('App Hide')
})
</script>

<style>
page {
  background-color: #f9fafb;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Helvetica Neue',
    sans-serif;
  color: #111827;
  font-size: 28rpx;
}
.card {
  background: #fff;
  border-radius: 24rpx;
  padding: 28rpx;
  margin-bottom: 24rpx;
}
.section-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #111827;
  margin-bottom: 20rpx;
}
.btn-primary {
  background: #2563eb;
  color: #fff;
  border-radius: 16rpx;
  height: 88rpx;
  line-height: 88rpx;
  font-size: 30rpx;
  text-align: center;
}
.btn-primary::after {
  border: none;
}
.stamp-square {
  width: 48rpx;
  height: 48rpx;
  border: 4rpx solid #2563eb;
  transform: rotate(45deg);
}
.stamp-round {
  width: 48rpx;
  height: 48rpx;
  border: 4rpx solid #f59e0b;
  border-radius: 50%;
}
.stamp-combo {
  width: 48rpx;
  height: 48rpx;
  position: relative;
}
.stamp-combo .sq {
  position: absolute;
  inset: 0;
  border: 4rpx solid #10b981;
}
.stamp-combo .rd {
  position: absolute;
  inset: 6rpx;
  border: 4rpx solid #10b981;
  border-radius: 50%;
}
</style>
