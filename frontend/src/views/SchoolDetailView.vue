<template>
  <div>
    <!-- Loading state -->
    <div v-if="loading" class="py-20 text-center text-gray-400 text-sm">
      Loading school details...
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
      {{ error }}
    </div>

    <div v-else-if="school">
      <!-- Back button -->
      <button
        @click="goBack"
        class="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-800
               font-medium mb-6 transition-colors"
      >
        ← Back to Search
      </button>

      <!-- School name + status -->
      <div class="flex items-start justify-between gap-4 mb-4">
        <h1 class="text-2xl font-bold text-gray-900 leading-snug">
          {{ school.school_name }}
        </h1>
        <!-- <span
          class="shrink-0 mt-1 text-xs font-medium px-2.5 py-1 rounded-full"
          :class="statusBadgeClass"
        >
          {{ statusBadgeLabel }}
        </span> -->
        <span
          class="shrink-0 mt-1 text-base font-semibold px-3 py-1.5 rounded-full"
          :class="statusBadgeClass"
        >
          {{ statusBadgeLabel }}
        </span>
      </div>

      <!-- Status description -->
      <p class="text-sm text-gray-500 mb-6">
        {{ school.school_status_description }}
      </p>

      <!-- Amber lifecycle banner — relocated schools only -->
      <div
        v-if="school.school_status === 'relocated_gap'"
        class="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6"
      >
        <p class="text-sm font-medium text-amber-800 mb-1">
          Temporary relocation gap
        </p>
        <p class="text-sm text-amber-700">
          This school suspended P1 intake from
          <strong>{{ school.inactive_from_year }}</strong> and will
          resume in <strong>{{ school.inactive_to_year + 1 }}</strong>.
        </p>
      </div>

      <!-- Sections grid -->
      <div class="grid grid-cols-1 gap-5 sm:grid-cols-2">

        <!-- School overview -->
        <div class="section-card sm:col-span-2">
          <h2 class="section-title">School Overview</h2>
          <div class="grid grid-cols-1 gap-y-3 sm:grid-cols-2">
            <DetailRow label="Address" :value="school.address" />
            <DetailRow label="Postal code" :value="school.postal_code?.toString()" />
            <DetailRow label="Zone" :value="school.zone_code" />
            <DetailRow label="Estate" :value="school.dgp_code" />
            <DetailRow label="Type" :value="school.type_code" />
            <DetailRow label="Nature" :value="school.nature_code" />
            <DetailRow label="Session" :value="school.session_code" />
            <div>
              <p class="detail-label">Mother tongue</p>
              <p class="detail-value">
                {{ [school.mothertongue1_code, school.mothertongue2_code, school.mothertongue3_code]
                  .filter(Boolean).join(' · ') || '—' }}
              </p>
            </div>
          </div>

          <!-- Programme badges -->
          <div class="mt-4">
            <p class="detail-label mb-1.5">Special programmes</p>
            <div class="flex flex-wrap gap-2">
              <span v-if="school.sap_ind" class="badge bg-amber-50 text-amber-700">SAP</span>
              <span v-if="school.gifted_ind" class="badge bg-teal-50 text-teal-700">GEP</span>
              <span v-if="school.autonomous_ind" class="badge bg-purple-50 text-purple-700">Autonomous</span>
              <!-- <span v-if="school.ip_ind" class="badge bg-teal-50 text-teal-700">IP</span> -->
              <!-- <span v-if="!school.sap_ind && !school.autonomous_ind && !school.gifted_ind && !school.ip_ind" -->
              <span v-if="!school.sap_ind && !school.autonomous_ind && !school.gifted_ind"
                class="text-sm text-gray-800">N/A</span>
            </div>
          </div>
        </div>

        <!-- Contact details -->
        <div class="section-card" v-if="hasContactInfo">
          <h2 class="section-title">Contact</h2>
          <div class="space-y-3">
            <div v-if="school.url_address">
              <p class="detail-label">Website</p>
              <a :href="school.url_address" target="_blank" rel="noopener"
                class="text-sm text-blue-600 hover:underline break-all">
                {{ school.url_address }}
              </a>
            </div>
            <DetailRow label="Email" :value="school.email_address" />
            <DetailRow label="Phone" :value="formatPhone(school.telephone_no, school.telephone_no_2)" />
            <DetailRow label="Fax" :value="formatPhone(school.fax_no, school.fax_no_2)" />
          </div>
        </div>

        <!-- Transport -->
        <div class="section-card " v-if="school.mrt_desc || school.bus_desc">
        <!-- <div class="section-card sm:col-start-2" v-if="school.mrt_desc || school.bus_desc"> -->
          <h2 class="section-title">Transport</h2>
          <div class="space-y-3">
            <div v-if="school.mrt_desc">
              <p class="detail-label">MRT</p>
              <p class="detail-value">{{ school.mrt_desc }}</p>
            </div>
            <div v-if="school.bus_desc">
              <p class="detail-label">Bus services</p>
              <p class="detail-value">{{ school.bus_desc }}</p>
            </div>
          </div>
        </div>

        <!-- Leadership -->
        <div class="section-card sm:col-span-2" v-if="hasLeadership">
          <h2 class="section-title">Leadership</h2>
          <div class="grid grid-cols-1 gap-y-3 sm:grid-cols-2">
            <div class="sm:col-span-2">
              <DetailRow label="Principal" :value="school.principal_name" />
            </div>
            <DetailRow label="First Vice-Principal" :value="school.first_vp_name" />
            <DetailRow label="Second Vice-Principal" :value="school.second_vp_name" />
            <DetailRow label="Third Vice-Principal" :value="school.third_vp_name" />
            <DetailRow label="Fourth Vice-Principal" :value="school.fourth_vp_name" />
            <DetailRow label="Fifth Vice-Principal" :value="school.fifth_vp_name" />
            <DetailRow label="Sixth Vice-Principal" :value="school.sixth_vp_name" />
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DetailRow from '../components/DetailRow.vue'
import apiClient from '../services/api'

const route = useRoute()
const router = useRouter()

const school = ref(null)
const loading = ref(true)
const error = ref(null)

onMounted(async () => {
  try {
    const name = decodeURIComponent(route.params.schoolName)
    const response = await apiClient.get(`/schools/${encodeURIComponent(name)}`)
    school.value = response.data
  } catch (err) {
    error.value = err.response?.status === 404
      ? 'School not found. Please go back and try again.'
      : 'Unable to load school details. Please try again.'
  } finally {
    loading.value = false
  }
})

function goBack() {
  router.push('/schools')
}

function formatPhone(primary, secondary) {
  if (!primary) return null
  return secondary ? `${primary} / ${secondary}` : primary
}

const statusBadgeClass = computed(() => {
  if (!school.value) return ''
  if (school.value.is_active) return 'bg-green-100 text-green-700'
  if (school.value.school_status === 'merged') return 'bg-red-100 text-red-600'
  if (school.value.school_status === 'relocated_gap') return 'bg-amber-100 text-amber-700'
  return 'bg-gray-100 text-gray-500'
})

const statusBadgeLabel = computed(() => {
  if (!school.value) return ''
  if (school.value.is_active) return 'Active'
  if (school.value.school_status === 'merged') return 'Merged'
  if (school.value.school_status === 'relocated_gap') return 'Relocated'
  return 'Inactive'
})

const hasContactInfo = computed(() => {
  if (!school.value) return false
  return school.value.url_address
    || school.value.email_address
    || school.value.telephone_no
    || school.value.fax_no
})

const hasLeadership = computed(() => {
  if (!school.value) return false
  return school.value.principal_name || school.value.first_vp_name
})
</script>
