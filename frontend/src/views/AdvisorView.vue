<template>
  <div>
    <!-- Page header -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900">P1 Advisor</h1>
      <p class="text-gray-500 text-sm mt-1">
        Ask any question about Singapore Primary 1 registration, balloting,
        or school selection.
      </p>
    </div>

    <!-- Disclaimer banner -->
    <div class="bg-blue-50 border border-blue-100 rounded-xl p-4 mb-6">
      <p class="text-xs text-blue-700 leading-relaxed">
        <span class="font-semibold">Note:</span> The advisor uses historical
        balloting data (2019–2025) and MOE published guidelines. Always verify
        with <a href="https://www.moe.gov.sg/primary/p1-registration"
          target="_blank"
          rel="noopener"
          class="underline hover:text-blue-900">MOE's official P1 registration portal</a>
        before making decisions.
      </p>
    </div>

    <!-- Main layout: single column mobile, two column desktop -->
    <div class="flex flex-col gap-6 lg:flex-row lg:items-start">

      <!-- Left: Chat panel -->
      <div class="flex-1">

        <!-- Question input -->
        <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-5 mb-4">
          <label class="block text-xs font-medium text-gray-600 mb-2">
            Your question
            <span class="text-gray-400 ml-1">({{ question.length }}/500)</span>
          </label>
          <textarea
            v-model="question"
            rows="3"
            maxlength="500"
            placeholder="e.g. What is Phase 2C and who can apply? Can a PR family apply?"
            class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2
                   focus:outline-none focus:ring-2 focus:ring-blue-500
                   focus:border-transparent resize-none text-gray-700
                   bg-white text-gray-700 placeholder-gray-400"
          />

          <!-- Optional school context -->
          <div class="mt-3">
            <label class="block text-xs font-medium text-gray-600 mb-1">
              School name
              <span class="text-gray-400 font-normal">(optional — for school-specific questions)</span>
            </label>
            <input
              v-model="schoolName"
              type="text"
              placeholder="e.g. NAN CHIAU PRIMARY SCHOOL"
              class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2
                     focus:outline-none focus:ring-2 focus:ring-blue-500
                     focus:border-transparent text-gray-700
                     bg-white text-gray-700 placeholder-gray-400"
            />
          </div>

          <div v-if="validationError" class="mt-2 text-xs text-red-500">
            {{ validationError }}
          </div>

          <button
            @click="askAdvisor"
            :disabled="loading || question.trim().length < 3"
            class="mt-4 px-5 py-2 bg-blue-600 text-white text-sm font-medium
                   rounded-lg hover:bg-blue-700 disabled:opacity-50
                   transition-colors"
          >
            {{ loading ? 'Thinking...' : 'Ask Advisor' }}
          </button>
        </div>

        <!-- Answer area -->
        <div
          v-if="loading"
          class="bg-white rounded-xl border border-gray-200 shadow-sm p-5"
        >
          <div class="flex items-center gap-2 text-gray-400 text-sm">
            <svg class="animate-spin h-4 w-4 text-blue-500"
              xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10"
                stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor"
                d="M4 12a8 8 0 018-8v8z"/>
            </svg>
            Searching knowledge base and generating response...
          </div>
          <p v-if="showSlowWarning" class="text-xs text-gray-400 mt-2 italic">
            This is taking a little longer than usual — please wait...
          </p>
        </div>

        <div
          v-else-if="answer"
          class="bg-white rounded-xl border border-gray-200 shadow-sm p-5"
        >
          <!-- Answer text -->
          <p class="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap mb-4">
            {{ answer }}
          </p>

          <!-- School context indicator -->
          <div
            v-if="schoolContextUsed"
            class="mb-3 inline-flex items-center gap-1.5 text-xs
                   bg-green-50 text-green-700 px-2.5 py-1 rounded-full"
          >
            <span>✓</span>
            <span>School balloting data included</span>
          </div>

          <!-- Disclaimer -->
          <p class="text-xs text-gray-400 italic mt-3">
            {{ disclaimer }}
          </p>
        </div>

        <!-- Error state -->
        <div
          v-else-if="error"
          class="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm"
        >
          {{ error }}
        </div>

      </div>

      <!-- Right: Sources panel (desktop only) -->
      <div
        v-if="sources.length > 0"
        class="hidden lg:block lg:w-72 shrink-0"
      >
        <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <h2 class="text-xs font-semibold text-gray-500 uppercase
                     tracking-wide mb-3">
            Sources
          </h2>
          <p class="text-xs text-gray-400 mb-3">
            This answer was grounded in the following MOE documents:
          </p>
          <div class="space-y-2">
            <div
              v-for="(source, index) in uniqueSources"
              :key="index"
              class="bg-gray-50 rounded-lg p-3"
            >
              <p class="text-xs font-medium text-gray-700 leading-snug mb-1">
                {{ formatTopic(source.topic) }}
              </p>
              <a
                v-if="source.source_url"
                :href="source.source_url"
                target="_blank"
                rel="noopener"
                class="text-xs text-blue-500 hover:underline break-all"
              >
                MOE source ↗
              </a>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import apiClient from '../services/api'

// Session identity — generated once on page mount, unused until Week 5
const sessionId = ref(null)
onMounted(() => {
  sessionId.value = crypto.randomUUID()
})

// Form state
const question = ref('')
const schoolName = ref('')
const validationError = ref(null)

// Response state
const answer = ref(null)
const sources = ref([])
const schoolContextUsed = ref(false)
const disclaimer = ref('')
const loading = ref(false)
const error = ref(null)

// Deduplicate sources by source_file for display
const uniqueSources = computed(() => {
  const seen = new Set()
  return sources.value.filter(s => {
    if (seen.has(s.source_file)) return false
    seen.add(s.source_file)
    return true
  })
})

const showSlowWarning = ref(false)
let slowTimer = null

function formatTopic(topic) {
  // Shorten long MOE topic strings for display
  return topic
    .replace('Primary 1 (P1) registration - ', '')
    .replace('Primary 1 (P1) registration', 'P1 Registration Overview')
}

function validate() {
  if (question.value.trim().length < 3) {
    validationError.value = 'Please enter a question with at least 3 characters.'
    return false
  }
  validationError.value = null
  return true
}

async function askAdvisor() {
  if (!validate()) return

  loading.value = true
  showSlowWarning.value = false
  error.value = null
  answer.value = null
  sources.value = []
  schoolContextUsed.value = false
  disclaimer.value = ''

  // Show warning if response takes more than 5 seconds
  slowTimer = setTimeout(() => {
    showSlowWarning.value = true
  }, 5000)

  try {
    const response = await apiClient.post('/advisor', {
      question: question.value.trim(),
      school_name: schoolName.value.trim() || null,
      session_id: sessionId.value,        // wired now, activated Week 5
      conversation_history: null,         // wired now, activated Week 5
    }, {
      timeout: 30000,   // 30 seconds for advisor only
    })

    answer.value = response.data.answer
    sources.value = response.data.sources
    schoolContextUsed.value = response.data.school_context_used
    disclaimer.value = response.data.disclaimer

  } catch (err) {
    error.value = err.response?.data?.detail
      ?? 'Unable to reach the advisor. Please try again.'
  } finally {
    loading.value = false
    showSlowWarning.value = false
    clearTimeout(slowTimer)
  }
}
</script>