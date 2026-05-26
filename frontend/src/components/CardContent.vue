<template>
  <div>
    <!-- School name and status badge -->
    <div class="flex items-start justify-between gap-3 mb-3">
      <h3 class="font-semibold text-gray-900 text-sm leading-snug">
        {{ school.school_name }}
      </h3>
      <span
        class="shrink-0 text-sm font-medium px-2 py-0.5 rounded-full"
        :class="statusBadgeClass"
      >
        {{ statusBadgeLabel }}
      </span>
    </div>

    <!-- Attributes row — hidden if all values are null or UNKNOWN -->
    <div
      v-if="hasAttributes"
      class="flex flex-wrap gap-2 mb-3"
    >
      <span v-if="school.zone_code && school.zone_code !== 'UNKNOWN'"
        class="badge bg-blue-50 text-blue-700">
        {{ school.zone_code }}
      </span>
      <span v-if="school.dgp_code && school.dgp_code !== 'UNKNOWN'"
        class="badge bg-blue-50 text-blue-700">
        {{ school.dgp_code }}
      </span>
      <span v-if="school.type_code" class="badge bg-gray-100 text-gray-600">
        {{ school.type_code }}
      </span>
      <span v-if="school.nature_code" class="badge bg-gray-100 text-gray-600">
        {{ school.nature_code }}
      </span>
    </div>

    <!-- Special programme indicators -->
    <div class="flex flex-wrap gap-2">
      <span v-if="school.sap_ind" class="badge bg-amber-50 text-amber-700">SAP</span>
      <span v-if="school.gifted_ind" class="badge bg-teal-50 text-teal-700">GEP</span>
      <span v-if="school.autonomous_ind" class="badge bg-purple-50 text-purple-700">Autonomous</span>
      <!-- <span v-if="school.ip_ind" class="badge bg-teal-50 text-teal-700">IP</span> -->
    </div>

    <!-- Active description -->
    <p v-if="school.is_active" class="mt-3 text-xs text-gray-900 italic">
      Tap to view more school details
    </p>

    <!-- Inactive description -->
    <p v-if="!school.is_active && school.school_status != 'merged'"
      class="mt-3 text-xs text-gray-900 italic">
      {{ school.school_status_description }}
       <br/><br/>
      Tap to view more school details
    </p>
   
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  school: {
    type: Object,
    required: true,
  },
})

const statusBadgeClass = computed(() => {
  if (props.school.is_active) return 'bg-green-100 text-green-700'
  if (props.school.school_status === 'merged') return 'bg-red-100 text-red-600'
  if (props.school.school_status === 'relocated_gap') return 'bg-amber-100 text-amber-700'
  return 'bg-gray-100 text-gray-500'
})

const statusBadgeLabel = computed(() => {
  if (props.school.is_active) return 'Active'
  if (props.school.school_status === 'merged') return 'Merged'
  if (props.school.school_status === 'relocated_gap') return 'Relocated'
  return 'Inactive'
})

const hasAttributes = computed(() => {
  const s = props.school
  const meaningful = (val) => val && val !== 'UNKNOWN'
  return meaningful(s.zone_code)
    || meaningful(s.dgp_code)
    || meaningful(s.type_code)
    || meaningful(s.nature_code)
})
</script>
