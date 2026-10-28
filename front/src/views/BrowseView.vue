<template>
  <div>
    <div class="page-head">
      <div>
        <p class="eyebrow">校园服务</p>
        <h1>信息广场</h1>
        <p class="muted">让遗失的物品，回到熟悉的人身边。</p>
      </div>
      <router-link :to="auth.isLoggedIn ? '/publish' : '/login'">
        <el-button type="primary">发布信息</el-button>
      </router-link>
    </div>

    <el-form :inline="true" :model="filters" class="filters" @submit.prevent="load">
      <el-form-item label="关键词" class="search">
        <el-input v-model="filters.q" placeholder="搜索物品名称或特征" maxlength="100" clearable />
      </el-form-item>
      <el-form-item label="信息类型">
        <el-select v-model="filters.kind" placeholder="全部类型" clearable style="width: 120px">
          <el-option label="招领" value="FOUND" />
          <el-option label="寻物" value="LOST" />
        </el-select>
      </el-form-item>
      <el-form-item label="物品类别">
        <el-select v-model="filters.category" placeholder="全部类别" clearable style="width: 130px">
          <el-option v-for="c in auth.categories" :key="c" :label="c" :value="c" />
        </el-select>
      </el-form-item>
      <el-form-item label="地点">
        <el-select v-model="filters.location" placeholder="全部地点" clearable filterable style="width: 150px">
          <el-option v-for="loc in locations" :key="loc" :label="loc" :value="loc" />
        </el-select>
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 120px">
          <el-option label="待认领" value="OPEN" />
          <el-option label="已认领" value="CLAIMED" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" native-type="submit">筛选</el-button>
        <el-button @click="reset">重置</el-button>
      </el-form-item>
    </el-form>

    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px">
      <h2 style="margin: 0">最新信息</h2>
      <span class="muted">{{ items.length }} 条记录</span>
    </div>

    <div class="item-grid">
      <ItemCard v-for="item in items" :key="item.id" :item="item" />
      <div v-if="items.length === 0" class="empty">
        <h2>没有找到相关信息</h2>
        <p>请尝试其他关键词或筛选条件。</p>
        <router-link to="/">查看全部信息</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import http from '../api/http'
import { useAuthStore } from '../stores/auth'
import ItemCard from '../components/ItemCard.vue'
import type { Item } from '../types'

const auth = useAuthStore()
const items = ref<Item[]>([])
const locations = ref<string[]>([])
const filters = reactive({ q: '', kind: '', category: '', location: '', status: '' })

async function load() {
  const { data } = await http.get<{ items: Item[]; locations: string[] }>('/items', { params: filters })
  items.value = data.items
  locations.value = data.locations
}

function reset() {
  filters.q = ''
  filters.kind = ''
  filters.category = ''
  filters.location = ''
  filters.status = ''
  load()
}

onMounted(load)
</script>
