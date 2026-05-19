<template>
  <!-- Tappable card for active and relocated schools -->
  <router-link
    v-if="school.school_status !== 'merged'"
    :to="`/schools/${encodeURIComponent(school.school_name)}`"
    class="block bg-white rounded-xl border border-gray-200 shadow-sm p-5
           hover:shadow-md hover:border-blue-200 transition-all"
  >
    <CardContent :school="school" />
  </router-link>

  <!-- Non-tappable card for merged schools -->
  <div
    v-else
    class="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden"
  >
    <div class="p-5">
      <CardContent :school="school" />
    </div>
    <!-- Disabled footer strip -->
    <div class="px-5 py-2.5 bg-gray-50 border-t border-gray-200">
      <p class="text-xs text-gray-400">
        {{ school.school_status_description }}
      </p>
    </div>
  </div>
</template>

<script setup>
import CardContent from './CardContent.vue'

defineProps({
  school: {
    type: Object,
    required: true,
  },
})
</script>
