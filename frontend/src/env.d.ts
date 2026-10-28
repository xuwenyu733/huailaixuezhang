/// <reference types="vite/client" />

declare module '*.vue' {
  import { DefineComponent } from 'vue'
  // eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/ban-types
  const component: DefineComponent<{}, {}, any>
  export default component
}

declare module '@/utils/request' {
  type Opt = { noAuth?: boolean; noVerify?: boolean }
  type Fn = (api: string, data?: any, opt?: Opt) => Promise<any>
  const request: {
    get: Fn
    post: Fn
    put: Fn
    delete: Fn
    [key: string]: Fn
  }
  export default request
}
