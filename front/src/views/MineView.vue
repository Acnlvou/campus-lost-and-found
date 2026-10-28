<template>
  <div>
    <div class="page-head">
      <div>
        <p class="eyebrow">个人记录</p>
        <h1>我的发布</h1>
      </div>
      <router-link to="/publish"><el-button type="primary">发布信息</el-button></router-link>
    </div>

    <div class="record-list">
      <router-link v-for="item in items" :key="item.id" class="record" :to="`/items/${item.id}`">
        <div>
          <span class="muted">{{ auth.label(item.kind) }} · {{ item.location }}</span>
          <h2>{{ item.title }}</h2>
        </div>
        <StatusTag :status="item.pub_status" />
      </router-link>
      <div v-if="items.length === 0" class="empty">
        <h2>还没有发布信息</h2>
        <router-link to="/publish">发布第一条信息</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import http from '../api/http'
import { useAuthStore } from '../stores/auth'
import StatusTag from '../components/StatusTag.vue'
import type { Item } from '../types'

const auth = useAuthStore()
const items = ref<Item[]>([])

async function load() {
  const { data } = await http.get<{ items: Item[] }>('/mine')
  items.value = data.items
}

onMounted(load)
</script>
