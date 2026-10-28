// #ifdef H5
let VUE_APP_WS_URL_DEFAULT = `ws://${location.hostname}?type=user`
// #endif

let openPlantGrass = '-openPlantGrass-'

// 网络接口修改此字符 小程序域名要求https
let httpApi = 'https://www.wiidu.com.cn';//'https://mall.haykz.com' mall.wiidu.com.cn

// 聊天接口修改此字符 小程序聊天要求wss 例如：wss://mer.crmeb.net
let wsApi = 'wss://www.wiidu.com.cn'

// 请求域名 格式： https://您的域名
let HTTP_REQUEST_URL = httpApi
let VUE_APP_WS_URL = `${wsApi}?type=user`

// #ifdef H5
//H5 开发调试走 Vite devServer 代理（见项目根目录 vite.config.js），避免跨域；
//发布时若接口为独立域名，改为 httpApi 并让服务器配置 CORS
HTTP_REQUEST_URL = ''
// 聊天长连接地址
VUE_APP_WS_URL = wsApi ? `${wsApi}?type=user` : VUE_APP_WS_URL_DEFAULT
// #endif

const HEADER = {
    'Content-Type': 'application/json;charset=UTF-8;',
    //#ifdef H5
    'Form-type': navigator.userAgent.toLowerCase().indexOf("micromessenger") !== -1 ? 'wechat' : 'h5',
    //#endif
    //#ifdef MP
    'Form-type': 'routine',
    //#endif
    //#ifdef APP-PLUS
    'Form-type': 'app',
    //#endif
}

// 回话密钥名称 请勿修改此配置
const TOKENNAME = 'X-Token'

// 缓存时间 0 永久
const EXPIRE = 0

export {
    HTTP_REQUEST_URL,
    VUE_APP_WS_URL,
    openPlantGrass,
    HEADER,
    TOKENNAME,
    EXPIRE
}

export default {
    HTTP_REQUEST_URL,
    VUE_APP_WS_URL,
    openPlantGrass,
    HEADER,
    TOKENNAME,
    EXPIRE
}
