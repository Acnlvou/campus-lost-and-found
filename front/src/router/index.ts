import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import BrowseView from '../views/BrowseView.vue'
import LoginView from '../views/LoginView.vue'
import PublishView from '../views/PublishView.vue'
import DetailView from '../views/DetailView.vue'
import MineView from '../views/MineView.vue'
import ApplicationsView from '../views/ApplicationsView.vue'
import AdminView from '../views/AdminView.vue'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    requiresAdmin?: boolean
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'browse', component: BrowseView },
    { path: '/login', name: 'login', component: LoginView },
    { path: '/publish', name: 'publish', component: PublishView, meta: { requiresAuth: true } },
    { path: '/items/:id', name: 'detail', component: DetailView },
    { path: '/mine', name: 'mine', component: MineView, meta: { requiresAuth: true } },
    { path: '/applications', name: 'applications', component: ApplicationsView, meta: { requiresAuth: true } },
    { path: '/admin', name: 'admin', component: AdminView, meta: { requiresAuth: true, requiresAdmin: true } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.ready) {
    await auth.fetchSession()
  }
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return { name: 'browse' }
  }
  return true
})

export default router
