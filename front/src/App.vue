<template>
  <div class="layout">
    <header class="header">
      <div class="nav-wrap">
        <router-link to="/" class="brand">
          校园失物招领<span>CAMPUS LOST &amp; FOUND</span>
        </router-link>
        <nav class="nav" aria-label="主导航">
          <router-link to="/" :class="{ selected: $route.name === 'browse' }">信息广场</router-link>
          <router-link to="/mine" :class="{ selected: $route.name === 'mine' }">我的发布</router-link>
          <router-link to="/applications" :class="{ selected: $route.name === 'applications' }">我的申请</router-link>
          <router-link v-if="auth.isAdmin" to="/admin" :class="{ selected: $route.name === 'admin' }">审核</router-link>
        </nav>
        <div class="account">
          <template v-if="auth.isLoggedIn">
            <span>{{ auth.user?.name }}</span>
            <el-button link @click="logout">退出</el-button>
          </template>
          <router-link v-else to="/login">
            <el-button type="primary" size="small">登录</el-button>
          </router-link>
        </div>
      </div>
    </header>

    <main class="main">
      <router-view />
    </main>

    <footer class="footer">
      <span>校园失物招领系统 · 课程演示</span>
      <span>{{ auth.version }} · 演示数据，非真实失物信息</span>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const router = useRouter()

async function logout() {
  try {
    await auth.logout()
    ElMessage.success('已退出登录')
    router.push('/')
  } catch (e) {
    /* 拦截器已提示错误 */
  }
}
</script>
