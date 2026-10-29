<template>
  <div>
    <div class="page-head">
      <div>
        <p class="eyebrow">管理员</p>
        <h1>信息审核</h1>
        <p class="muted">审核用户提交的失物或招领信息，审核通过后才公开。</p>
      </div>
    </div>

    <div class="record-list">
      <div v-for="item in items" :key="item.id" class="record">
        <div>
          <span class="muted">{{ auth.label(item.kind) }} · {{ item.category }} · {{ item.location }} · 发布者 {{ item.owner_name }}</span>
          <h2><router-link :to="`/items/${item.id}`">{{ item.title }}</router-link></h2>
        </div>
        <div style="display: flex; align-items: center; gap: 10px; flex-shrink: 0">
          <StatusTag :status="item.pub_status" />
          <template v-if="item.pub_status === 'PENDING'">
            <el-button type="primary" size="small" @click="review(item.id, 'approve')">通过</el-button>
            <el-button size="small" @click="review(item.id, 'reject')">拒绝</el-button>
          </template>
        </div>
      </div>
      <div v-if="items.length === 0" class="empty"><h2>暂无信息</h2></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../api/http'
import { useAuthStore } from '../stores/auth'
import StatusTag from '../components/StatusTag.vue'
import type { Item } from '../types'

const auth = useAuthStore()
const items = ref<Item[]>([])

async function load() {
  const { data } = await http.get<{ items: Item[] }>('/admin/items')
  items.value = data.items
}

async function review(itemId: number, decision: string) {
  let review_reason: string | undefined = undefined

  if (decision === 'approve') {
    try {
      await ElMessageBox.confirm('确认通过该信息并公开？', '审核', { type: 'warning' })
    } catch (e) {
      return
    }
  } else {
    // 拒绝：弹出输入框填写理由
    try {
      review_reason = await ElMessageBox.prompt('请输入拒绝理由', '拒绝审核', {
        type: 'warning',
        inputPlaceholder: '例如：信息描述模糊、无关内容等',
      })
    } catch (e) {
      return
    }
  }

  await http.post(`/items/${itemId}/review`, {
    decision,
    review_reason
  })
  ElMessage.success('审核已保存')
  await load()
}

onMounted(load)
</script>
