<template>
  <div class="flex flex-col h-[calc(100vh-10rem)]">

    <!-- Page header -->
    <div class="mb-4 shrink-0">
      <h1 class="text-2xl font-bold text-gray-900">P1 Advisor</h1>
      <p class="text-gray-500 text-sm mt-1">
        Ask any question about Singapore Primary 1 registration,
        balloting, or school selection.
      </p>
    </div>

    <!-- Chat message area — fixed height, internal scroll -->
    <div
      ref="chatContainer"
      class="flex-1 overflow-y-auto space-y-4 pb-4 pr-1 min-h-0"
    >
      <!-- Empty state with suggestion prompts -->
      <div
        v-if="messages.length === 0"
        class="flex flex-col items-center justify-center h-full
               text-center text-gray-400 px-4"
      >
        <div class="text-4xl mb-3">🏫</div>
        <p class="text-sm font-medium text-gray-500 mb-3">
          Ask me anything about P1 registration
        </p>
        <div class="space-y-2 w-full max-w-sm">
          <button
            v-for="suggestion in suggestions"
            :key="suggestion"
            @click="useSuggestion(suggestion)"
            class="block w-full text-xs text-left bg-gray-50
                   hover:bg-blue-50 hover:text-blue-700
                   border border-gray-200 rounded-lg px-3 py-2
                   transition-colors"
          >
            {{ suggestion }}
          </button>
        </div>
      </div>

      <!-- Message bubbles -->
      <template v-for="(msg, index) in messages" :key="index">

        <!-- Parent question — right aligned -->
        <div class="flex justify-end">
          <div
            class="max-w-[80%] bg-blue-600 text-white rounded-2xl
                   rounded-tr-sm px-4 py-3 text-sm leading-relaxed"
          >
            <p>{{ msg.question }}</p>
            <!-- School chips in question bubble -->
            <div
              v-if="msg.schoolNames && msg.schoolNames.length > 0"
              class="mt-2 flex flex-wrap gap-1"
            >
              <span
                v-for="name in msg.schoolNames"
                :key="name"
                class="text-xs bg-blue-500 px-2 py-0.5 rounded-full"
              >
                {{ name }}
              </span>
            </div>
          </div>
        </div>

        <!-- Advisor response — left aligned -->
        <div class="flex justify-start">
          <div class="max-w-[85%]">

            <!-- Response bubble -->
            <div
              class="bg-white border border-gray-200 rounded-2xl
                     rounded-tl-sm px-4 py-3 text-sm text-gray-800
                     leading-relaxed shadow-sm"
            >
              <!-- Loading -->
              <div
                v-if="msg.loading"
                class="flex flex-col gap-1"
              >
                <div class="flex items-center gap-2 text-gray-400">
                  <svg class="animate-spin h-4 w-4 text-blue-500"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12"
                      r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor"
                      d="M4 12a8 8 0 018-8v8z"/>
                  </svg>
                  <span>Thinking...</span>
                </div>
                <p
                  v-if="msg.showSlowWarning"
                  class="text-xs text-gray-400 italic"
                >
                  This is taking a little longer — please wait...
                </p>
              </div>

              <!-- Answer -->
              <p
                v-if="!msg.loading && msg.answer"
                class="whitespace-pre-wrap"
              >
                {{ msg.answer }}
              </p>

              <!-- Error -->
              <p
                v-if="!msg.loading && msg.error"
                class="text-red-600 text-sm"
              >
                {{ msg.error }}
              </p>

              <!-- School context badge -->
              <div
                v-if="!msg.loading && msg.schoolContextUsed"
                class="mt-2 inline-flex items-center gap-1 text-xs
                       text-green-700 bg-green-50 px-2 py-0.5
                       rounded-full"
              >
                <span>✓</span>
                <span>School data included</span>
              </div>
            </div>

            <!-- Collapsible sources -->
            <div
              v-if="!msg.loading && msg.sources && msg.sources.length > 0"
              class="mt-1 ml-1"
            >
              <button
                @click="toggleSources(index)"
                class="text-xs text-gray-900 hover:text-gray-600
                       transition-colors flex items-center gap-1"
              >
                <span>{{ msg.showSources ? '▲' : '▼' }}</span>
                <span>
                  {{ msg.showSources ? 'Hide' : 'View' }} sources
                  ({{ uniqueSourceCount(msg.sources) }})
                </span>
              </button>
              <div v-if="msg.showSources" class="mt-2 space-y-1.5">
                <div
                  v-for="(source, si) in uniqueSources(msg.sources)"
                  :key="si"
                  class="bg-gray-50 rounded-lg px-3 py-2"
                >
                  <p class="text-xs font-medium text-gray-600
                             leading-snug">
                    {{ formatTopic(source.topic) }}
                  </p>
                  
                  <a v-if="source.source_url"
                    :href="source.source_url"
                    target="_blank"
                    rel="noopener"
                    class="text-xs text-blue-500 hover:underline"
                  >
                    MOE source ↗
                  </a>
                </div>
              </div>
            </div>

            <!-- Per-message disclaimer -->
            <p
              v-if="!msg.loading && msg.answer"
              class="text-xs text-gray-900 mt-1 ml-1 italic"
            >
              Based on historical data (2019–2025). Verify with MOE.
            </p>

          </div>
        </div>

      </template>
    </div>

    <!-- Fixed input area -->
    <div
      class="shrink-0 pt-3 border-t border-gray-200 bg-gray-50
             -mx-4 px-4 pb-3 mt-2 space-y-2"
    >
      <!-- School multi-select -->
      <div>
        <label class="block text-xs font-medium text-gray-700 mb-1">
          (Optional) Compare schools
          <span class="font-normal text-gray-700">
            — select up to 3 schools to include their ballot history
            and details in the response
          </span>
        </label>
        <MultiSelect
          v-model="selectedSchools"
          :options="schoolOptions"
          option-label="display_label"
          option-value="school_name"
          placeholder="Search and select schools..."
          filter
          :selection-limit="3"
          :max-selected-labels="3"
          class="w-full text-sm"
        >
          <template #option="{ option }">
            <div class="flex flex-col">
              <span class="text-sm text-gray-800">
                {{ option.school_name }}
              </span>
              <span class="text-xs text-gray-400">
                {{ option.dgp_code }}
              </span>
            </div>
          </template>
          <template #value="{ value }">
            <span v-if="!value || value.length === 0"
              class="text-gray-400 text-sm">
              Search and select schools...
            </span>
            <span v-else class="text-sm text-gray-700">
              {{ value.join(', ') }}
            </span>
          </template>
        </MultiSelect>
        <p
          v-if="selectedSchools.length === 3"
          class="text-xs text-amber-600 mt-1"
        >
          Maximum of 3 schools selected.
        </p>
      </div>

      <!-- Textarea input -->
      <div>
        <textarea
          v-model="question"
          maxlength="500"
          placeholder="Ask about P1 registration, balloting, or schools..."
          @keydown.enter.exact.prevent="askAdvisor"
          class="w-full text-sm border border-gray-300 rounded-xl
                 px-3 py-2 focus:outline-none focus:ring-2
                 focus:ring-blue-500 focus:border-transparent
                 resize-none bg-white text-gray-700
                 placeholder-gray-400
                 min-h-[44px] sm:min-h-[88px]"
        />
        <p class="text-xs text-gray-400 mt-0.5">
          Characters Count · {{ question.length }}/500
        </p>
      </div>

      <!-- Ask button — full width, below textarea -->
      <button
        @click="askAdvisor"
        :disabled="loading || question.trim().length < 3"
        class="w-full py-2.5 bg-blue-600 text-white text-sm
               font-medium rounded-xl hover:bg-blue-700
               disabled:opacity-50 transition-colors"
      >
        {{ loading ? 'Thinking...' : 'Ask Advisor' }}
      </button>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import MultiSelect from 'primevue/multiselect'
import apiClient from '../services/api'
import { metadata, fetchMetadata } from '../services/metadata'

// Session identity — wired now, activated Week 5
const sessionId = ref(null)
onMounted(async () => {
  sessionId.value = crypto.randomUUID()
  await fetchMetadata()
})

// School options — add display_label combining name + estate
const schoolOptions = computed(() =>
  (metadata.value?.schools ?? []).map(s => ({
    ...s,
    display_label: `${s.school_name} (${s.dgp_code})`,
  }))
)

// Form state
const question = ref('')
const selectedSchools = ref([])
const loading = ref(false)

// Chat messages — local UI state
const messages = ref([])
const chatContainer = ref(null)

const suggestions = [
  'What is Phase 2C and who can apply?',
  'How does balloting work when a school is oversubscribed?',
  'What is the difference between SAP and autonomous schools?',
  'How does distance from school affect priority?',
]

function useSuggestion(text) {
  question.value = text
}

function formatTopic(topic) {
  return topic
    .replace('Primary 1 (P1) registration - ', '')
    .replace('Primary 1 (P1) registration', 'P1 Registration Overview')
}

function uniqueSources(sources) {
  const seen = new Set()
  return sources.filter(s => {
    if (seen.has(s.source_file)) return false
    seen.add(s.source_file)
    return true
  })
}

function uniqueSourceCount(sources) {
  return new Set(sources.map(s => s.source_file)).size
}

function toggleSources(index) {
  messages.value[index].showSources = !messages.value[index].showSources
}

async function scrollToBottom() {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

async function askAdvisor() {
  if (question.value.trim().length < 3 || loading.value) return

  const currentQuestion = question.value.trim()
  const currentSchools = [...selectedSchools.value]

  // Augment question with school context instruction (Option A)
  let augmentedQuestion = currentQuestion
  if (currentSchools.length > 0) {
    augmentedQuestion =
      currentQuestion +
      ` Please also provide specific ballot risk and school information ` +
      `for the following schools: ${currentSchools.join(', ')}.`
  }

  // Add message to chat immediately
  const msgIndex = messages.value.length
  messages.value.push({
    question: currentQuestion,       // display original question
    schoolNames: currentSchools,
    answer: null,
    sources: [],
    schoolContextUsed: false,
    loading: true,
    showSlowWarning: false,
    showSources: false,
    error: null,
  })

  question.value = ''
  loading.value = true
  await scrollToBottom()

  const slowTimer = setTimeout(() => {
    if (messages.value[msgIndex]) {
      messages.value[msgIndex].showSlowWarning = true
    }
  }, 5000)

  try {
    const response = await apiClient.post('/advisor', {
      question: augmentedQuestion,   // send augmented question to API
      school_names: currentSchools.length > 0 ? currentSchools : null,
      session_id: sessionId.value,
      conversation_history: null,
    }, {
      timeout: 30000,
    })

    messages.value[msgIndex].answer = response.data.answer
    messages.value[msgIndex].sources = response.data.sources
    messages.value[msgIndex].schoolContextUsed =
      response.data.school_context_used

  } catch (err) {
    messages.value[msgIndex].error =
      err.response?.data?.detail ??
      'Unable to reach the advisor. Please try again.'
  } finally {
    messages.value[msgIndex].loading = false
    messages.value[msgIndex].showSlowWarning = false
    clearTimeout(slowTimer)
    loading.value = false
    await scrollToBottom()
  }
}
</script>