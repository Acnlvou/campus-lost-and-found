<template>
  <div>
    <router-link to="/" class="muted">返回信息广场</router-link>

    <div v-if="detail" class="detail-layout">
      <section>
        <div class="meta" style="margin-top: 18px; justify-content: flex-start; gap: 8px">
          <span class="badge" :class="`kind-${detail.item.kind}`">{{ auth.label(detail.item.kind) }}</span>
          <span v-if="detail.item.pub_status !== 'APPROVED'" class="status" :class="detail.item.pub_status">{{ auth.label(detail.item.pub_status) }}</span>
          <span class="status" :class="detail.item.status">{{ auth.label(detail.item.status) }}</span>
        </div>
        <h1>{{ detail.item.title }}</h1>

        <!-- 新增：拒绝理由展示 -->
        <div v-if="detail.item.pub_status === 'REJECTED' && detail.item.review_reason" style="color: #f56c6c; background: #fef0f0; padding:10px 14px; border-radius:6px; margin:12px 0;">
          <strong>拒绝理由：</strong>{{ detail.item.review_reason }}
        </div>

        <dl class="facts">
          <div><dt>物品类别</dt><dd>{{ detail.item.category }}</dd></div>
          <div><dt>地点</dt><dd>{{ detail.item.location }}</dd></div>
          <div><dt>事件时间</dt><dd>{{ datetimeOf(detail.item.event_time) }}</dd></div>
          <div><dt>发布者</dt><dd>{{ detail.item.owner_name }}</dd></div>
        </dl>

        <h2>物品描述</h2>
        <p class="prose">{{ detail.item.description }}</p>

        <template v-if="detail.owner && detail.history.length">
          <h2 style="margin-top: 40px">状态记录</h2>
          <ul class="history">
            <li v-for="row in detail.history" :key="row.id">
              <time>{{ datetimeOf(row.created_at) }}</time>
              <span>{{ row.action }} · {{ row.detail }}</span>
            </li>
          </ul>
        </template>
      </section>

      <aside class="claim-panel">
        <h2>{{ detail.owner ? '认领管理' : '认领物品' }}</h2>

        <template v-if="!auth.isLoggedIn">
          <p>登录后可提交认领申请。</p>
          <router-link to="/login"><el-button type="primary">登录</el-button></router-link>
        </template>
        <template v-else-if="detail.item.pub_status !== 'APPROVED'">
          <p class="muted">{{ detail.item.pub_status === 'PENDING' ? '该信息正在等待管理员审核，暂未公开。' : '该信息已被拒绝，未公开。' }}</p>
        </template>
        <template v-else-if="detail.item.kind === 'LOST'">
          <p class="muted">这是一条寻物信息，不接受认领申请。</p>
        </template>
        <template v-else-if="detail.item.status === 'CLAIMED'">
          <p class="muted">该物品已完成认领。</p>
        </template>
        <template v-else-if="detail.owner && !auth.allow_self">
          <p class="muted">你是发布者，可在下方审核申请。</p>
        </template>
        <template v-else-if="detail.claims.length === 0">
          <el-form label-position="top" @submit.prevent="submitClaim">
            <el-form-item label="认领说明">
              <el-input v-model="note" type="textarea" :rows="4" maxlength="500" placeholder="提供能够证明物品属于你的特征。" />
            </el-form-item>
            <el-button type="primary" native-type="submit" :loading="claimLoading">提交认领申请</el-button>
          </el-form>
        </template>

        <template v-if="detail.claims.length">
          <h3>{{ detail.owner ? '收到的申请' : '我的申请' }}</h3>
          <article v-for="claim in detail.claims" :key="claim.id" class="application">
            <div class="meta" style="justify-content: space-between">
              <strong>{{ claim.applicant_name }}</strong>
              <span class="status" :class="claim.status">{{ auth.label(claim.status) }}</span>
            </div>
            <p class="prose">{{ claim.note }}</p>
            <time class="muted">{{ dateOf(claim.created_at) }}</time>
            <div v-if="detail.owner && claim.status === 'PENDING' && detail.item.status === 'OPEN'" style="margin-top: 12px">
              <el-button type="primary" size="small" @click="review(claim.id, 'approve')">确认认领</el-button>
              <el-button size="small" @click="review(claim.id, 'reject')">拒绝</el-button>
            </div>
          </article>
        </template>
        <p v-else-if="detail.owner" class="muted">暂未收到认领申请。</p>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../api/http'
import { useAuthStore } from '../stores/auth'
import { dateOf, datetimeOf } from '../utils/format'
import type { DetailData } from '../types'

const auth = useAuthStore()
const route = useRoute()
const detail = ref<DetailData | null>(null)
const note = ref('')
const claimLoading = ref(false)

async function load() {
  const { data } = await http.get<DetailData>(`/items/${route.params.id}`)
  detail.value = data

  // 读取query参数，刚发布成功弹窗提示
  if (route.query.notice === 'pending') {
    ElMessage.success('提交成功！信息正在等待管理员审核')
  }
}

async function submitClaim() {
  claimLoading.value = true
  try {
    await http.post(`/items/${route.params.id}/claims`, { note: note.value })
    note.value = ''
    ElMessage.success('申请已提交')
    await load()
  } catch (e) {
    /* 拦截器已提示错误 */
  } finally {
    claimLoading.value = false
  }
}

async function review(claimId: number, decision: string) {
  if (decision === 'approve') {
    try {
      await ElMessageBox.confirm('确认该申请后，其他待处理申请将关闭。是否确认？', '确认认领', { type: 'warning' })
    } catch (e) {
      return
    }
  }
  await http.post(`/claims/${claimId}/review`, { decision })
  ElMessage.success('审核已保存')
  await load()
}

onMounted(load)
</script>
