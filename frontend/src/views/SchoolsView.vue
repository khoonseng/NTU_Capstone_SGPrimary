<template>
  <div>
    <!-- Page header -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900">Browse Schools</h1>
      <p class="text-gray-500 text-sm mt-1">
        Filter active primary schools by zone, type, and special programmes.
      </p>
    </div>

    <!-- Filter form -->
    <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-5 mb-6">
      <div class="grid grid-cols-2 gap-4 sm:grid-cols-4 mb-4">
        <!-- Zone -->
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Zone</label>
          <select v-model="filters.zone_code" class="filter-select">
            <option value="">All zones</option>
            <option value="NORTH">North</option>
            <option value="SOUTH">South</option>
            <option value="EAST">East</option>
            <option value="WEST">West</option>
          </select>
        </div>

        <!-- Type -->
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">School type</label>
          <select v-model="filters.type_code" class="filter-select">
            <option value="">All types</option>
            <option value="GOVERNMENT">Government</option>
            <option value="GOVERNMENT-AIDED SCH">Govt-aided</option>
          </select>
        </div>

        <!-- Nature -->
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Nature</label>
          <select v-model="filters.nature_code" class="filter-select">
            <option value="">All</option>
            <option value="CO-ED SCHOOL">Co-ed</option>
            <option value="BOYS SCHOOL">Boys</option>
            <option value="GIRLS SCHOOL">Girls</option>
          </select>
        </div>

        <!-- DGP code -->
        <div>
          <label class="block text-xs font-medium text-gray-600 mb-1">Estate</label>
          <input
            v-model="filters.dgp_code"
            type="text"
            placeholder="e.g. SENG KANG"
            class="filter-select"
          />
        </div>
      </div>

      <!-- Special programme toggles -->
      <div class="flex flex-wrap gap-3 mb-4">
        <label class="toggle-label">
          <input type="checkbox" v-model="filters.sap_ind" class="mr-1.5" />
          SAP
        </label>
        <label class="toggle-label">
          <input type="checkbox" v-model="filters.autonomous_ind" class="mr-1.5" />
          Autonomous
        </label>
        <label class="toggle-label">
          <input type="checkbox" v-model="filters.gifted_ind" class="mr-1.5" />
          GEP
        </label>
        <label class="toggle-label">
          <input type="checkbox" v-model="filters.ip_ind" class="mr-1.5" />
          IP
        </label>
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
</template>

<script setup>
import { ref, reactive } from 'vue'
import apiClient from '../services/api'
import SchoolCard from '../components/SchoolCard.vue'

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
  ip_ind: false,
})

function buildParams() {
  const params = {}
  if (filters.zone_code) params.zone_code = filters.zone_code
  if (filters.type_code) params.type_code = filters.type_code
  if (filters.nature_code) params.nature_code = filters.nature_code
  if (filters.dgp_code) params.dgp_code = filters.dgp_code.toUpperCase().trim()
  if (filters.sap_ind) params.sap_ind = true
  if (filters.autonomous_ind) params.autonomous_ind = true
  if (filters.gifted_ind) params.gifted_ind = true
  if (filters.ip_ind) params.ip_ind = true
  return params
}

async function fetchSchools() {
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
    ip_ind: false,
  })
  schools.value = []
  searched.value = false
  error.value = null
}
</script>
