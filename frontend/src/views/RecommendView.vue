<template>
  <div>
    <!-- Page header -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-900">School Recommendations</h1>
      <p class="text-gray-500 text-sm mt-1">
        Find schools by location and see ballot difficulty based on historical data.
      </p>
    </div>

    <!-- Filter form -->
    <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-5 mb-6">
      <div v-if="metadataLoading" class="text-sm text-gray-400 mb-4">
        Loading filter options...
      </div>
      <div v-else-if="metadataError" class="text-sm text-red-500 mb-4">
        {{ metadataError }}
      </div>

      <div v-else>
        <!-- Row 1: location + school filters -->
        <div class="grid grid-cols-2 gap-4 sm:grid-cols-4 mb-4">
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Zone</label>
            <select v-model="filters.zone_code" @change="onZoneChange" class="filter-select">
              <option value="">All zones</option>
              <option v-for="zone in metadata?.zones" :key="zone" :value="zone">
                {{ zone }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Estate</label>
            <select v-model="filters.dgp_code" class="filter-select">
              <option value="">All estates</option>
              <option v-for="estate in availableEstates" :key="estate" :value="estate">
                {{ estate }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">School type</label>
            <select v-model="filters.type_code" class="filter-select">
              <option value="">All types</option>
              <option v-for="type in metadata?.type_codes" :key="type" :value="type">
                {{ type }}
              </option>
            </select>
          </div>
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

        <!-- Row 2: phase + balloting -->
        <div class="grid grid-cols-2 gap-4 sm:grid-cols-4 mb-4">
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Phase</label>
            <select v-model="filters.phase" @change="onPhaseChange" class="filter-select">
              <option value="">All phases</option>
              <option value="2B">2B</option>
              <option value="2C">2C</option>
              <option value="2C(S)">2C(S)</option>
              <option value="3">3</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">
              Balloting history
              <span v-if="!filters.phase" class="text-gray-700 ml-1">(select phase first)</span>
            </label>
            <select
              v-model="filters.has_balloting_3yr"
              :disabled="!filters.phase"
              class="filter-select disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <option :value="null">Any</option>
              <option :value="true">Balloted in last 3 years</option>
              <option :value="false">Not balloted in last 3 years</option>
            </select>
          </div>
        </div>

        <!-- Special programme toggles -->
        <div class="grid grid-cols-1 gap-3 mb-4 sm:grid-cols-3">
          <label class="flex flex-col gap-0.5 cursor-pointer select-none">
            <div class="flex items-center gap-1.5">
              <input type="checkbox" v-model="filters.sap_ind" />
              <span class="text-sm font-medium text-gray-900">SAP</span>
            </div>
            <span class="text-xs text-gray-900 leading-snug">Higher Chinese curriculum alongside English</span>
          </label>
          <label class="flex flex-col gap-0.5 cursor-pointer select-none">
            <div class="flex items-center gap-1.5">
              <input type="checkbox" v-model="filters.autonomous_ind" />
              <span class="text-sm font-medium text-gray-900">Autonomous</span>
            </div>
            <span class="text-xs text-gray-900 leading-snug">Flexibility to introduce special programmes</span>
          </label>
          <label class="flex flex-col gap-0.5 cursor-pointer select-none">
            <div class="flex items-center gap-1.5">
              <input type="checkbox" v-model="filters.gifted_ind" />
              <span class="text-sm font-medium text-gray-900">GEP</span>
            </div>
            <span class="text-xs text-gray-900 leading-snug">For students identified as gifted in P3</span>
          </label>
          <!-- <label class="flex flex-col gap-0.5 cursor-pointer select-none">
            <div class="flex items-center gap-1.5">
              <input type="checkbox" v-model="filters.ip_ind" />
              <span class="text-sm font-medium text-gray-900">IP</span>
            </div>
            <span class="text-xs text-gray-900 leading-snug">6-year through-train to JC, skipping O-levels</span>
          </label> -->
        </div>

        <!-- Validation message -->
        <div v-if="validationError" class="text-xs text-red-500 mb-3">
          {{ validationError }}
        </div>

        <!-- Action buttons -->
        <div class="flex gap-3">
          <button
            @click="fetchRecommendations"
            :disabled="loading"
            class="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg
                   hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {{ loading ? 'Searching...' : 'Search' }}
          </button>
          <button
            @click="resetFilters"
            class="px-5 py-2 bg-white border border-gray-300 text-gray-600 text-sm
                   font-medium rounded-lg hover:bg-gray-50 transition-colors"
          >
            Reset
          </button>
        </div>
      </div>
    </div>

    <!-- API error -->
    <div v-if="error"
      class="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 text-red-700 text-sm">
      {{ error }}
    </div>

    <!-- Results header + legend -->
    <div v-if="searched && !loading && results.length > 0">
      <div class="flex items-center justify-between mb-3">
        <p class="text-sm text-gray-900">
          {{ results.length }} school{{ results.length !== 1 ? 's' : '' }} found
          <span v-if="filters.phase"> — Phase {{ filters.phase }} · last 3 years</span>
          <span v-else> — most recent year per phase</span>
        </p>
      </div>

      <!-- Collapsible legend -->
      <div class="bg-blue-50 border border-blue-100 rounded-xl mb-5 overflow-hidden">
        <!-- <span class="w-full flex items-center justify-between px-4 py-3 text-left">
          <span class="text-sm font-medium text-blue-700">
              What does Ballot Risk mean?
          </span>
        </span> -->
        <button
          @click="legendOpen = !legendOpen"
          class="w-full flex items-center justify-between px-4 py-3 text-left"
        >
          <span class="text-sm font-medium text-blue-700">
            What does Ballot Risk mean?
          </span>
          <span class="text-blue-400 text-lg">{{ legendOpen ? '−' : '+' }}</span>
        </button>
        <div v-if="legendOpen" class="px-4 pb-4 grid grid-cols-1 gap-2 sm:grid-cols-3">
          <div class="flex items-start gap-2">
            <span class="badge bg-red-100 text-red-700 mt-0.5 shrink-0">HIGH</span>
            <p class="text-xs text-blue-700 leading-snug">
              Balloted in all 3 of the last 3 years with average subscription rate above 1.2×.
              Competition is intense — plan carefully.
            </p>
          </div>
          <div class="flex items-start gap-2">
            <span class="badge bg-amber-100 text-amber-700 mt-0.5 shrink-0">MEDIUM</span>
            <p class="text-xs text-blue-700 leading-snug">
              Balloted in at least 1 of the last 3 years with subscription rate above 1.2×.
              Monitor closely — balloting is possible.
            </p>
          </div>
          <div class="flex items-start gap-2">
            <span class="badge bg-green-100 text-green-700 mt-0.5 shrink-0">LOW</span>
            <p class="text-xs text-blue-700 leading-snug">
              No balloting in the last 3 years.
              Places available without balloting based on recent trends.
            </p>
          </div>
          <div class="flex items-start gap-2 sm:col-span-3">
            <span class="badge bg-gray-100 text-gray-500 mt-0.5 shrink-0">N/A</span>
            <p class="text-xs text-blue-700 leading-snug">
              Phase was not opened — all places were filled in earlier phases.
              No balloting risk applies.
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- ── MODE 1 results — no phase selected ── -->
    <div v-if="mode === 1 && results.length > 0" class="grid grid-cols-1 gap-5">
      <div
        v-for="school in results"
        :key="school.school_name"
        class="bg-white rounded-xl border border-gray-200 shadow-sm p-5"
      >
        <!-- School header -->
        <div class="flex items-start justify-between gap-3 mb-4">
          <div>
            <h3 class="font-semibold text-gray-900">{{ school.school_name }}</h3>
            <p class="text-xs text-gray-900 mt-0.5">
              {{ [school.zone_code, school.dgp_code].filter(Boolean).join(' · ') }}
            </p>
          </div>
          <div class="flex gap-2 shrink-0 flex-wrap justify-end">
            <span v-if="school.school_attributes?.sap_ind"
              class="badge bg-amber-50 text-amber-700">SAP</span>
            <span v-if="school.school_attributes?.autonomous_ind"
              class="badge bg-purple-50 text-purple-700">Autonomous</span>
            <span v-if="school.school_attributes?.gifted_ind"
              class="badge bg-indigo-50 text-indigo-700">GEP</span>
            <span v-if="school.school_attributes?.ip_ind"
              class="badge bg-teal-50 text-teal-700">IP</span>
          </div>
        </div>

        <!-- Phase table header -->
        <div class="grid grid-cols-6 gap-2 pb-1 border-b border-gray-100 mb-1">
          <p class="text-xs font-medium text-gray-400">Phase</p>
          <p class="text-xs font-medium text-gray-400 text-right">Vacancy</p>
          <p class="text-xs font-medium text-gray-400 text-right">Applied</p>
          <p class="text-xs font-medium text-gray-400 text-right">Taken</p>
          <p class="text-xs font-medium text-gray-400 text-right">Subscription Rate</p>
          <p class="text-xs font-medium text-gray-400 text-right">Ballot Risk</p>
        </div>

        <!-- Phase rows -->
        <div class="divide-y divide-gray-50">
          <div
            v-for="phaseData in school.phases"
            :key="phaseData.phase"
            class="grid grid-cols-6 gap-2 py-2 items-center"
          >
            <p class="text-xs font-semibold text-gray-600">{{ phaseData.phase }}</p>

            <template v-if="isPhaseOpened(phaseData.years[0])">
              <p class="text-xs text-gray-700 text-right">
                {{ phaseData.years[0]?.vacancy ?? '—' }}
              </p>
              <p class="text-xs text-gray-700 text-right">
                {{ phaseData.years[0]?.applied ?? '—' }}
              </p>
              <p class="text-xs text-gray-700 text-right">
                {{ phaseData.years[0]?.taken ?? '—' }}
              </p>
              <p class="text-xs text-gray-700 text-right">
                {{ phaseData.years[0]?.subscription_rate != null
                  ? phaseData.years[0].subscription_rate.toFixed(2) + 'x' : '—' }}
              </p>
              <div class="flex justify-end">
                <RiskBadge :level="phaseData.years[0]?.ballot_risk_level" />
              </div>
            </template>

            <template v-else>
              <p class="text-xs text-gray-900 text-right col-span-4">Phase not opened</p>
              <div class="flex justify-end">
                <span class="badge bg-gray-100 text-gray-400">N/A</span>
              </div>
            </template>
          </div>
        </div>

        <!-- Most recent year footnote -->
        <p class="text-xs text-gray-900 mt-3">
          Based on {{ mostRecentYear(school.phases) }} registration data
        </p>
      </div>
    </div>

    <!-- ── MODE 2 results — phase selected ── -->
    <div v-if="mode === 2 && results.length > 0" class="grid grid-cols-1 gap-5">
      <div
        v-for="school in results"
        :key="school.school_name"
        class="bg-white rounded-xl border border-gray-200 shadow-sm p-5"
      >
        <!-- School header -->
        <div class="flex items-start justify-between gap-3 mb-4">
          <div>
            <h3 class="font-semibold text-gray-900">{{ school.school_name }}</h3>
            <p class="text-xs text-gray-400 mt-0.5">
              {{ [school.zone_code, school.dgp_code].filter(Boolean).join(' · ') }}
            </p>
          </div>
          <RiskBadge :level="school.latest_year?.ballot_risk_level" />
        </div>

        <!-- Trend summary -->
        <div class="grid grid-cols-2 gap-3 mb-4 sm:grid-cols-4">
          <StatCell
            label="Avg subscription rate"
            :value="school.trend?.subscription_rate_3yr_avg
              ? school.trend.subscription_rate_3yr_avg.toFixed(2) + 'x' : null"
          />
          <StatCell
            label="Balloted (last 3yr)"
            :value="school.trend?.ballot_occurrences_last_3yr != null
              ? school.trend.ballot_occurrences_last_3yr + ' / 3' : null"
          />
          <StatCell
            label="Avg vacancy"
            :value="school.trend?.vacancy_3yr_avg
              ? Math.round(school.trend.vacancy_3yr_avg).toString() : null"
          />
          <div class="bg-gray-50 rounded-lg p-3">
            <p class="text-xs text-gray-400 mb-1">Vacancy trend</p>
            <p class="text-sm font-semibold"
              :class="vacancyTrendClass(school.trend?.vacancy_yoy_change)">
              {{ formatVacancyTrend(school.trend?.vacancy_yoy_change) }}
            </p>
          </div>
        </div>

        <!-- 3-year history table -->
        <div class="overflow-x-auto">
          <table class="w-full text-xs">
            <thead>
              <tr class="text-gray-400 border-b border-gray-100">
                <th class="text-left pb-2 font-medium">Year</th>
                <th class="text-right pb-2 font-medium">Vacancy</th>
                <th class="text-right pb-2 font-medium">Applied</th>
                <th class="text-right pb-2 font-medium">Taken</th>
                <th class="text-right pb-2 font-medium">Subscription Rate</th>
                <th class="text-right pb-2 font-medium">Ballot</th>
                <th class="text-right pb-2 font-medium">Chance</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-50">
              <tr
                v-for="yr in school.history"
                :key="yr.registration_year"
                :class="yr.is_current_year ? 'text-gray-300' : 'text-gray-700'"
              >
                <td class="py-2 font-medium">
                  {{ yr.registration_year }}
                  <span v-if="yr.is_current_year" class="ml-1 text-gray-300">(current)</span>
                </td>
                <td class="text-right py-2">{{ yr.vacancy ?? '—' }}</td>
                <td class="text-right py-2">{{ yr.applied ?? '—' }}</td>
                <td class="text-right py-2">{{ yr.taken ?? '—' }}</td>
                <td class="text-right py-2">
                  {{ yr.subscription_rate ? yr.subscription_rate.toFixed(2) + 'x' : '—' }}
                </td>
                <td class="text-right py-2">{{ yr.ballot_scenario_code ?? '—' }}</td>
                <td class="text-right py-2">
                  {{ yr.ballot_chance_pct ? yr.ballot_chance_pct + '%' : '—' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div
      v-else-if="searched && !loading && results.length === 0"
      class="text-center py-16 text-gray-400"
    >
      <p class="text-lg mb-1">No schools found</p>
      <p class="text-sm">Try adjusting your filters</p>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import apiClient from '../services/api'
import { metadata, metadataLoading, metadataError } from '../services/metadata'
import RiskBadge from '../components/RiskBadge.vue'
import StatCell from '../components/StatCell.vue'

const results = ref([])
const loading = ref(false)
const error = ref(null)
const searched = ref(false)
const mode = ref(0)
const validationError = ref(null)
const legendOpen = ref(false)

const filters = reactive({
  zone_code: '',
  dgp_code: '',
  type_code: '',
  nature_code: '',
  phase: '',
  has_balloting_3yr: null,
  sap_ind: false,
  autonomous_ind: false,
  gifted_ind: false,
  ip_ind: false,
})

const availableEstates = computed(() => {
  if (!metadata.value) return []
  if (!filters.zone_code) return metadata.value.all_estates
  return metadata.value.estates_by_zone[filters.zone_code] ?? []
})

function onZoneChange() { filters.dgp_code = '' }
function onPhaseChange() { if (!filters.phase) filters.has_balloting_3yr = null }

// Phase is considered "opened" if vacancy > 0 and is not the current year sentinel
function isPhaseOpened(yearRow) {
  if (!yearRow) return false
  if (yearRow.is_current_year) return false
  return yearRow.vacancy !== null && yearRow.vacancy > 0
}

function mostRecentYear(phases) {
  for (const phase of phases) {
    const nonCurrent = phase.years.find(y => !y.is_current_year)
    if (nonCurrent) return nonCurrent.registration_year
  }
  return '—'
}

function validate() {
  if (!filters.zone_code && !filters.dgp_code) {
    validationError.value = 'Please select at least a zone or estate to search.'
    return false
  }
  validationError.value = null
  return true
}

function buildParams() {
  const params = {}
  if (filters.zone_code) params.zone_code = filters.zone_code
  if (filters.dgp_code) params.dgp_code = filters.dgp_code
  if (filters.type_code) params.type_code = filters.type_code
  if (filters.nature_code) params.nature_code = filters.nature_code
  if (filters.phase) params.phase = filters.phase
  if (filters.has_balloting_3yr !== null && filters.phase)
    params.has_balloting_3yr = filters.has_balloting_3yr
  if (filters.sap_ind) params.sap_ind = true
  if (filters.autonomous_ind) params.autonomous_ind = true
  if (filters.gifted_ind) params.gifted_ind = true
  if (filters.ip_ind) params.ip_ind = true
  return params
}

async function fetchRecommendations() {
  if (!validate()) return
  loading.value = true
  error.value = null
  searched.value = true
  mode.value = filters.phase ? 2 : 1

  try {
    const response = await apiClient.get('/recommend', { params: buildParams() })
    results.value = response.data.recommendations
  } catch (err) {
    error.value = err.response?.data?.detail
      ?? 'Unable to reach the server. Please try again.'
    results.value = []
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  Object.assign(filters, {
    zone_code: '', dgp_code: '', type_code: '', nature_code: '',
    phase: '', has_balloting_3yr: null,
    sap_ind: false, autonomous_ind: false, gifted_ind: false, ip_ind: false,
  })
  results.value = []
  searched.value = false
  error.value = null
  validationError.value = null
  mode.value = 0
  legendOpen.value = false
}

function formatVacancyTrend(change) {
  if (change === null || change === undefined) return '—'
  if (change > 0) return `+${change}`
  return change.toString()
}

function vacancyTrendClass(change) {
  if (change === null || change === undefined) return 'text-gray-800'
  if (change > 0) return 'text-green-600'
  if (change < 0) return 'text-red-600'
  return 'text-gray-800'
}
</script>