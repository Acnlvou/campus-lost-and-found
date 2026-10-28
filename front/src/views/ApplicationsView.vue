<template>
  <div>
    <div class="page-head">
      <div>
        <p class="eyebrow">个人记录</p>
        <h1>我的申请</h1>
      </div>
      <router-link to="/" class="muted">浏览招领信息</router-link>
    </div>

    <div class="record-list">
      <router-link v-for="claim in claims" :key="claim.id" class="record" :to="`/items/${claim.item_id}`">
        <div>
          <span class="muted">{{ claim.location }} · {{ dateOf(claim.created_at) }}</span>
          <h2>{{ claim.title }}</h2>
          <p class="prose">{{ claim.note }}</p>
        </div>
        <StatusTag :status="claim.status" />
      </router-link>
      <div v-if="claims.length === 0" class="empty">
        <h2>还没有认领申请</h2>
        <router-link to="/">去信息广场看看</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import http from '../api/http'
import StatusTag from '../components/StatusTag.vue'
import { dateOf } from '../utils/format'
import type { Claim } from '../types'

const claims = ref<Claim[]>([])

async function load() {
  const { data } = await http.get<{ claims: Claim[] }>('/applications')
  claims.value = data.claims
}

onMounted(load)
</script>
