<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Navigation bar -->
    <nav class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
        <router-link to="/" class="text-lg font-bold text-blue-700 tracking-tight">
          SGPrimary
        </router-link>

        <!-- Desktop nav links -->
        <div class="hidden sm:flex gap-6">
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
            Recommendations
          </router-link>
          <router-link
            to="/advisor"
            class="text-sm font-medium text-gray-600 hover:text-blue-700 transition-colors"
            active-class="text-blue-700"
          >
            Advisor
          </router-link>
        </div>

        <!-- Mobile hamburger button -->
        <button
          @click="menuOpen = !menuOpen"
          class="sm:hidden p-2 rounded-lg text-gray-600 hover:bg-gray-100
                 transition-colors"
          aria-label="Toggle menu"
        >
          <!-- Hamburger icon -->
          <svg v-if="!menuOpen" xmlns="http://www.w3.org/2000/svg"
            class="h-5 w-5" fill="none" viewBox="0 0 24 24"
            stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round"
              d="M4 6h16M4 12h16M4 18h16"/>
          </svg>
          <!-- Close icon -->
          <svg v-else xmlns="http://www.w3.org/2000/svg"
            class="h-5 w-5" fill="none" viewBox="0 0 24 24"
            stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round"
              d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>

      <!-- Mobile dropdown menu -->
      <div
        v-if="menuOpen"
        class="sm:hidden border-t border-gray-100 bg-white px-4 py-3 space-y-1"
      >
        <router-link
          to="/schools"
          @click="menuOpen = false"
          class="block text-sm font-medium text-gray-600 hover:text-blue-700
                 py-2 transition-colors"
          active-class="text-blue-700"
        >
          Schools
        </router-link>
        <router-link
          to="/recommend"
          @click="menuOpen = false"
          class="block text-sm font-medium text-gray-600 hover:text-blue-700
                 py-2 transition-colors"
          active-class="text-blue-700"
        >
          Recommendations
        </router-link>
        <router-link
          to="/advisor"
          @click="menuOpen = false"
          class="block text-sm font-medium text-gray-600 hover:text-blue-700
                 py-2 transition-colors"
          active-class="text-blue-700"
        >
          Advisor
        </router-link>
      </div>
    </nav>

    <!-- Page content -->
    <main class="max-w-5xl mx-auto px-4 py-8">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { fetchMetadata } from './services/metadata'
import { onMounted } from 'vue'

const menuOpen = ref(false)

onMounted(() => {
  fetchMetadata()
})
</script>
