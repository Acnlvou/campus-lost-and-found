<template>
  <span class="status" :class="status">{{ label }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '../stores/auth'

const props = defineProps<{ status: string }>()
const auth = useAuthStore()
const label = computed(() => auth.label(props.status))
</script>
