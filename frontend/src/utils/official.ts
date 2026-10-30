import { OFFICIAL_SITE } from '@/constants/goods'

/**
 * 打开官网商品页。
 *
 * 小程序内不承接下单：H5 直接新窗口打开，小程序端复制链接让用户到浏览器打开。
 * 这样做是为了让价格、库存、售后统一在官网维护，避免两端商品信息不一致。
 */
export function openOfficial(url?: string) {
  const target = url || OFFICIAL_SITE
  // #ifdef H5
  window.open(target, '_blank')
  return
  // #endif
  // #ifndef H5
  uni.setClipboardData({
    data: target,
    success: () => {
      uni.showToast({ title: '官网链接已复制，请在浏览器打开', icon: 'none' })
    },
  })
  // #endif
}
