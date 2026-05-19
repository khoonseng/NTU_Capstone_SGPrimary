<template>
  <div>
    <!-- Page header -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Browse Schools</h1>
      <p class="text-gray-500 text-sm mt-1">
        Filter active primary schools by zone, estate, type, and special programmes.
      </p>
    </div>

    <!-- Tabs -->
    <div class="flex gap-1 mb-6 bg-gray-100 p-1 rounded-lg w-fit">
      <button
        @click="activeTab = 'active'"
        :class="activeTab === 'active'
          ? 'bg-white text-blue-700 shadow-sm'
          : 'text-gray-500 hover:text-gray-700'"
        class="px-5 py-2 text-sm font-medium rounded-md transition-all"
      >
        Active schools
      </button>
      <button
        @click="activeTab = 'inactive'"
        :class="activeTab === 'inactive'
          ? 'bg-white text-blue-700 shadow-sm'
          : 'text-gray-500 hover:text-gray-700'"
        class="px-5 py-2 text-sm font-medium rounded-md transition-all"
      >
        Inactive schools
      </button>
    </div>

    <!-- ── ACTIVE TAB ── -->
    <div v-if="activeTab === 'active'">

      <!-- Filter form -->
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-5 mb-6">

        <!-- Metadata loading state -->
        <div v-if="metadataLoading" class="text-sm text-gray-400 mb-4">
          Loading filter options...
        </div>
        <div v-else-if="metadataError" class="text-sm text-red-500 mb-4">
          {{ metadataError }}
        </div>

        <div v-else class="grid grid-cols-2 gap-4 sm:grid-cols-4 mb-4">

          <!-- Zone -->
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Zone</label>
            <select v-model="filters.zone_code" @change="onZoneChange" class="filter-select">
              <option value="">All zones</option>
              <option v-for="zone in metadata?.zones" :key="zone" :value="zone">
                {{ zone }}
              </option>
            </select>
          </div>

          <!-- Estate (cascades from zone) -->
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Estate</label>
            <select v-model="filters.dgp_code" class="filter-select">
              <option value="">All estates</option>
              <option v-for="estate in availableEstates" :key="estate" :value="estate">
                {{ estate }}
              </option>
            </select>
          </div>

          <!-- Type -->
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">School type</label>
            <select v-model="filters.type_code" class="filter-select">
              <option value="">All types</option>
              <option v-for="type in metadata?.type_codes" :key="type" :value="type">
                {{ type }}
              </option>
            </select>
          </div>

          <!-- Nature -->
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Nature</label>
            <select v-model="filters.nature_code" class="filter-select">
              <option value="">All</option>
              <option v-for="nature in metadata?.nature_codes" :key="nature" :value="nature">
                {{ nature }}
              </option>
            </select>
          </div>
        </div>

        <!-- Special programme toggles -->
        <div class="grid grid-cols-1 gap-3 mb-4 sm:grid-cols-3">
          <label class="flex flex-col gap-0.5 cursor-pointer select-none">
            <div class="flex items-center gap-1.5">
              <input type="checkbox" v-model="filters.sap_ind" />
              <span class="text-sm font-medium text-gray-700">SAP [Special Assistance Plan]</span>
            </div>
            <span class="text-xs text-gray-400 leading-snug">Higher Chinese curriculum alongside English</span>
          </label>
          <label class="flex flex-col gap-0.5 cursor-pointer select-none">
            <div class="flex items-center gap-1.5">
              <input type="checkbox" v-model="filters.autonomous_ind" />
              <span class="text-sm font-medium text-gray-700">Autonomous</span>
            </div>
            <span class="text-xs text-gray-400 leading-snug">Flexibility to introduce special programmes</span>
          </label>
          <label class="flex flex-col gap-0.5 cursor-pointer select-none">
            <div class="flex items-center gap-1.5">
              <input type="checkbox" v-model="filters.gifted_ind" />
              <span class="text-sm font-medium text-gray-700">GEP [Gifted Education Programme]</span>
            </div>
            <span class="text-xs text-gray-400 leading-snug">For students identified as gifted in P3</span>
          </label>
          <!--label class="flex flex-col gap-0.5 cursor-pointer select-none">
            <div class="flex items-center gap-1.5">
              <input type="checkbox" v-model="filters.ip_ind" />
              <span class="text-sm font-medium text-gray-700">IP [Integrated Programme]</span>
            </div>
            <span class="text-xs text-gray-400 leading-snug">6-year through-train to JC, skipping O-levels</span>
          </label-->
        </div>

        <!-- Action buttons -->
        <div class="flex gap-3">
          <button
            @click="fetchSchools"
            :disabled="loading"
            class="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {{ loading ? 'Searching...' : 'Search' }}
          </button>
          <button
            @click="resetFilters"
            class="px-5 py-2 bg-white border border-gray-300 text-gray-600 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
          >
            Reset
          </button>
        </div>
      </div>

      <!-- Error state -->
      <div v-if="error" class="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 text-red-700 text-sm">
        {{ error }}
      </div>

      <!-- Results summary -->
      <div v-if="schools.length > 0" class="text-sm text-gray-500 mb-4">
        {{ schools.length }} school{{ schools.length !== 1 ? 's' : '' }} found
      </div>

      <!-- Empty state -->
      <div
        v-else-if="searched && !loading"
        class="text-center py-16 text-gray-400"
      >
        <p class="text-lg mb-1">No schools found</p>
        <p class="text-sm">Try adjusting your filters</p>
      </div>

      <!-- Results grid -->
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <SchoolCard
          v-for="school in schools"
          :key="school.school_key"
          :school="school"
        />
      </div>
    </div>

    <!-- ── INACTIVE TAB ── -->
    <div v-if="activeTab === 'inactive'">
      <div v-if="inactiveLoading" class="text-sm text-gray-400 py-10 text-center">
        Loading inactive schools...
      </div>

      <div v-else-if="inactiveError" class="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
        {{ inactiveError }}
      </div>

      <div v-else>
        <p class="text-sm text-gray-500 mb-4">
          {{ inactiveSchools.length }} inactive school{{ inactiveSchools.length !== 1 ? 's' : '' }}
        </p>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <SchoolCard
            v-for="school in inactiveSchools"
            :key="school.school_key"
            :school="school"
          />
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import apiClient from '../services/api'
import { metadata, metadataLoading, metadataError } from '../services/metadata'
import SchoolCard from '../components/SchoolCard.vue'

const activeTab = ref('active')

// ── Active schools state ──
const schools = ref([])
const loading = ref(false)
const error = ref(null)
const searched = ref(false)

const filters = reactive({
  zone_code: '',
  type_code: '',
  nature_code: '',
  dgp_code: '',
  sap_ind: false,
  autonomous_ind: false,
  gifted_ind: false,
  // ip_ind: false,
})

// ── Inactive schools state ──
const inactiveSchools = ref([])
const inactiveLoading = ref(false)
const inactiveError = ref(null)
const inactiveFetched = ref(false)

// ── Cascading estate dropdown ──
const availableEstates = computed(() => {
  if (!metadata.value) return []
  if (!filters.zone_code) return metadata.value.all_estates
  return metadata.value.estates_by_zone[filters.zone_code] ?? []
})

function onZoneChange() {
  filters.dgp_code = ''  // reset estate when zone changes
}

// ── Active schools fetch ──
function buildParams() {
  const params = { is_active: true }
  if (filters.zone_code) params.zone_code = filters.zone_code
  if (filters.type_code) params.type_code = filters.type_code
  if (filters.nature_code) params.nature_code = filters.nature_code
  if (filters.dgp_code) params.dgp_code = filters.dgp_code
  if (filters.sap_ind) params.sap_ind = true
  if (filters.autonomous_ind) params.autonomous_ind = true
  if (filters.gifted_ind) params.gifted_ind = true
  // if (filters.ip_ind) params.ip_ind = true
  return params
}

async function fetchSchools() {
  sessionStorage.setItem('schoolFilters', JSON.stringify(filters))
  loading.value = true
  error.value = null
  searched.value = true

  try {
    const response = await apiClient.get('/schools', { params: buildParams() })
    schools.value = response.data.schools
  } catch (err) {
    error.value = err.response?.data?.detail
      ?? 'Unable to reach the server. Please try again.'
    schools.value = []
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  Object.assign(filters, {
    zone_code: '',
    type_code: '',
    nature_code: '',
    dgp_code: '',
    sap_ind: false,
    autonomous_ind: false,
    gifted_ind: false,
    // ip_ind: false,
  })
  schools.value = []
  searched.value = false
  error.value = null
}

// ── Inactive schools fetch — triggered when tab is first opened ──
async function fetchInactiveSchools() {
  if (inactiveFetched.value) return  // session cache — fetch once only

  inactiveLoading.value = true
  inactiveError.value = null

  try {
    const response = await apiClient.get('/schools', { params: { is_active: false } })
    inactiveSchools.value = response.data.schools
    inactiveFetched.value = true
  } catch (err) {
    inactiveError.value = err.response?.data?.detail
      ?? 'Unable to reach the server. Please try again.'
  } finally {
    inactiveLoading.value = false
  }
}

// Restore filters from sessionStorage on back navigation
onMounted(() => {
  const saved = sessionStorage.getItem('schoolFilters')
  if (saved) {
    const parsed = JSON.parse(saved)
    Object.assign(filters, parsed)
    fetchSchools()
  }
})

// Watch for tab switch to inactive — fetch on first open
watch(activeTab, (tab) => {
  if (tab === 'inactive') fetchInactiveSchools()
})
</script>
