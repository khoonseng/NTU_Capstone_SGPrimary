<template>
  <span
    v-if="level"
    class="text-xs font-semibold px-2.5 py-1 rounded-full"
    :class="badgeClass"
  >
    {{ level }}
  </span>
  <span v-else class="text-xs text-gray-400">—</span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  level: {
    type: String,
    default: null,
  },
})

const badgeClass = computed(() => {
  switch (props.level) {
    case 'HIGH':   return 'bg-red-100 text-red-700'
    case 'MEDIUM': return 'bg-amber-100 text-amber-700'
    case 'LOW':    return 'bg-green-100 text-green-700'
    default:       return 'bg-gray-100 text-gray-500'
  }
})
</script>
