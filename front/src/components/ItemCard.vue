<template>
  <article class="item-card">
    <router-link :to="`/items/${item.id}`" class="item-image" :aria-label="`查看${item.title}`">
      <img src="/images/objects.png" alt="校园常见物品演示图" width="960" height="480" />
      <span class="badge" :class="`kind-${item.kind}`">{{ auth.label(item.kind) }}</span>
    </router-link>
    <div class="item-body">
      <div class="meta">
        <span>{{ item.category }}</span>
        <StatusTag :status="item.status" />
      </div>
      <h3>
        <router-link :to="`/items/${item.id}`">{{ item.title }}</router-link>
      </h3>
      <p class="item-description">{{ item.description }}</p>
      <div class="item-bottom">
        <span>{{ item.location }}</span>
        <time>{{ dateOf(item.event_time) }}</time>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { useAuthStore } from '../stores/auth'
import { dateOf } from '../utils/format'
import StatusTag from './StatusTag.vue'
import type { Item } from '../types'

defineProps<{ item: Item }>()
const auth = useAuthStore()
</script>
