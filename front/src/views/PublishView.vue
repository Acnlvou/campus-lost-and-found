<template>
  <div class="narrow wide">
    <router-link to="/" class="muted">返回信息广场</router-link>
    <h1>发布信息</h1>
    <p class="muted">提交后将进入待审核，管理员审核通过后公开。</p>

    <el-form :model="form" label-position="top" @submit.prevent="submit">
      <el-form-item label="信息类型">
        <el-radio-group v-model="form.kind">
          <el-radio value="FOUND">我捡到了物品</el-radio>
          <el-radio value="LOST">我遗失了物品</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="标题">
        <el-input v-model="form.title" placeholder="例如：图书馆捡到白色耳机" maxlength="60" />
      </el-form-item>

      <el-form-item label="物品类别">
        <el-select v-model="form.category" placeholder="请选择类别" style="width: 100%">
          <el-option v-for="c in auth.categories" :key="c" :label="c" :value="c" />
        </el-select>
      </el-form-item>

      <el-form-item label="事件时间">
        <el-date-picker v-model="form.event_time" type="datetime" format="YYYY-MM-DDTHH:mm" value-format="YYYY-MM-DDTHH:mm" placeholder="选择事件时间" style="width: 100%" />
      </el-form-item>

      <el-form-item label="地点">
        <el-input v-model="form.location" placeholder="例如：图书馆二楼" maxlength="60" />
      </el-form-item>

      <el-form-item label="物品描述">
        <el-input v-model="form.description" type="textarea" :rows="5" maxlength="1000" placeholder="描述物品外观及拾得或遗失经过，请勿公开敏感个人信息。" />
      </el-form-item>

      <el-button type="primary" native-type="submit" :loading="loading">确认发布</el-button>
      <router-link to="/"><el-button>取消</el-button></router-link>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const loading = ref(false)
const form = reactive({
  kind: 'FOUND',
  title: '',
  category: '',
  event_time: '',
  location: '',
  description: '',
})

async function submit() {
  loading.value = true
  try {
    const { data } = await http.post<{ id: number; redirect: string }>('/items', form)
    ElMessage.success('信息已提交，等待管理员审核。')
    router.push(data.redirect || `/items/${data.id}`)
  } catch (e) {
    /* 拦截器已提示错误 */
  } finally {
    loading.value = false
  }
}
</script>
