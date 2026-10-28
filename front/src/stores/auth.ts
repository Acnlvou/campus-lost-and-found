import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import http, { setCsrf } from '../api/http'
import type { SessionData, User } from '../types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const csrf = ref('')
  const ready = ref(false)
  const version = ref('')
  const allow_self = ref(true)
  const categories = ref<string[]>([])
  const labels = ref<Record<string, string>>({})

  const isLoggedIn = computed(() => !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  function label(key: string): string {
    return labels.value[key] || key
  }

  async function fetchSession(): Promise<void> {
    const { data } = await http.get<SessionData>('/session')
    user.value = data.user
    csrf.value = data.csrf
    setCsrf(data.csrf)
    version.value = data.version
    allow_self.value = data.allow_self
    categories.value = data.categories || []
    labels.value = data.labels || {}
    ready.value = true
  }

  async function login(username: string, password: string): Promise<void> {
    await http.post('/login', { username, password })
    await fetchSession()
  }

  async function logout(): Promise<void> {
    try {
      await http.post('/logout')
    } finally {
      user.value = null
      await fetchSession()
    }
  }

  return {
    user,
    csrf,
    ready,
    version,
    allow_self,
    categories,
    labels,
    isLoggedIn,
    isAdmin,
    label,
    fetchSession,
    login,
    logout,
  }
})
