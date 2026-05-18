<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Navigation bar -->
    <nav class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
        <router-link to="/" class="text-lg font-bold text-blue-700 tracking-tight">
          SGPrimary
        </router-link>
        <div class="flex gap-6">
          <router-link
            to="/schools"
            class="text-sm font-medium text-gray-600 hover:text-blue-700 transition-colors"
            active-class="text-blue-700"
          >
            Schools
          </router-link>
          <router-link
            to="/recommend"
            class="text-sm font-medium text-gray-600 hover:text-blue-700 transition-colors"
            active-class="text-blue-700"
          >
            Recommend
          </router-link>
        </div>
      </div>
    </nav>

    <!-- Page content -->
    <main class="max-w-5xl mx-auto px-4 py-8">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { fetchMetadata } from './services/metadata'

onMounted(() => {
  fetchMetadata()
})
</script>
