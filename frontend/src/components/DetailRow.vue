<template>
  <div v-if="value">
    <p class="detail-label">{{ label }}</p>
    <p class="detail-value">{{ value }}</p>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: String, default: null },
})
</script>
