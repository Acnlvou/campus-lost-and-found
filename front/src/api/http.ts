import axios from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({
  baseURL: '/api',
  withCredentials: true,
})

let csrf = ''

export function setCsrf(token: string): void {
  csrf = token
}

http.interceptors.request.use((config) => {
  if (csrf) config.headers['X-CSRF-Token'] = csrf
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.error || '操作失败，请重试。'
    ElMessage.error(message)
    return Promise.reject(error)
  },
)

export default http
