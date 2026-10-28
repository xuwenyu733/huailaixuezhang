import {
    HTTP_REQUEST_URL,
    HEADER,
    TOKENNAME
} from '@/config/app';
// 回话密钥名称 请勿修改此配置
// let TOKENNAME = 'X-Token';
function baseRequest(url, method, data, {
    noAuth = false,
    noVerify = false
}) {
    console.log(method)
    let Url = HTTP_REQUEST_URL,
        header = HEADER;
    // if (!noAuth) {
    //     //登录过期自动登录
    //     if (!store.state.app.token && !checkLogin()) {
    //         toLogin();
    //         return Promise.reject({
    //             msg: '未登录'
    //         });
    //     }
    // }
    return new Promise((reslove, reject) => {
        uni.request({
            url: Url + '/zx/datainf/' + url,
            method: method || 'GET',
            header: header,
            // processData: false,
            // dataType: 'json',
            data: data || {},
            success: (res) => {
                // console.log(data)
                if (res.data && res.data.encode) {
                    try {
                        res.data = JSON.parse(decompress(res.data.data));
                    } catch (e) {
                        res.data = decompress(decodeURI(res.data.data));
                    }
                }
                if (noVerify)
                    reslove(res);
                else if (res.data.status == 200)
                    reslove(res.data, res);
                else if ([410000, 410001, 410002, 40000].indexOf(res.data.status) !== -1) {
                    reject(res.data);
                } else if (res.data.status == 501) {
                    reject(res.data);
                } else {
                    reject(res.data.message || '系统错误')
                };
            },
            fail: (message) => {
                reject('请求失败');
            }
        })
    });
}
const request = {};
['options', 'get', 'post', 'put', 'head', 'delete', 'trace', 'connect'].forEach((method) => {
    request[method] = (api, data, opt) => baseRequest(api, method, data, opt || {})
});
export default request;
