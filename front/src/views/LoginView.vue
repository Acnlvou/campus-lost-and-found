<template>
  <div class="narrow">
    <p class="eyebrow">个人账户</p>
    <h1>登录校园账户</h1>

    <el-form :model="form" label-position="top" @submit.prevent="submit">
      <el-form-item label="账号">
        <el-input v-model="form.username" autocomplete="username" maxlength="80" />
      </el-form-item>
      <el-form-item label="密码">
        <el-input v-model="form.password" type="password" autocomplete="current-password" maxlength="128" show-password />
      </el-form-item>
      <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">登录</el-button>
    </el-form>

    <aside class="demo-note">
      <h2>课程演示账户</h2>
      <p>林同学 alice · 陈同学 bob · 周同学 carol</p>
      <p>统一密码：<code>Campus123!</code></p>
      <p class="muted">演示账户不代表已完成校园身份核验。</p>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

async function submit() {
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    router.push(redirect)
  } catch (e) {
    /* 拦截器已提示错误 */
  } finally {
    loading.value = false
  }
}
</script>
