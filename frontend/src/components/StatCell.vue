<template>
  <div>
    <p class="text-xs text-gray-400 mb-0.5">{{ label }}</p>
    <p class="text-sm font-semibold text-gray-800">{{ value ?? '—' }}</p>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: String, default: null },
})
</script>
