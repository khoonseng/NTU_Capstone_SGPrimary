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
      <div v-if="metadataLoading" class="text-sm text-gray-400 mb-4">Loading filter options...</div>
      <div v-else-if="metadataError" class="text-sm text-red-500 mb-4">{{ metadataError }}</div>

      <div v-else>
        <div class="grid grid-cols-2 gap-4 sm:grid-cols-4 mb-4">
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Zone</label>
            <select v-model="filters.zone_code" @change="onZoneChange" class="filter-select">
              <option value="">All zones</option>
              <option v-for="zone in metadata?.zones" :key="zone" :value="zone">{{ zone }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Estate</label>
            <select v-model="filters.dgp_code" class="filter-select">
              <option value="">All estates</option>
              <option v-for="estate in availableEstates" :key="estate" :value="estate">{{ estate }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">School Type</label>
            <select v-model="filters.type_code" class="filter-select">
              <option value="">All types</option>
              <option v-for="type in metadata?.type_codes" :key="type" :value="type">{{ type }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">Nature</label>
            <select v-model="filters.nature_code" class="filter-select">
              <option value="">All</option>
              <option v-for="nature in metadata?.nature_codes" :key="nature" :value="nature">{{ nature }}</option>
            </select>
          </div>
        </div>

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
          <!-- <div>
            <label class="block text-xs font-medium text-gray-600 mb-1">
              Balloting History
              <span v-if="!filters.phase" class="text-gray-300 ml-1">(select phase first)</span>
            </label>
            <select
              v-model="filters.has_balloting_3yr"
              :disabled="!filters.phase"
              class="filter-select disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <option :value="null">All history</option>
              <option :value="true">Balloted in last 3 years</option>
              <option :value="false">Not balloted in last 3 years</option>
            </select>
          </div> -->
          <div v-if="filters.phase">
            <label class="block text-xs font-medium text-gray-600 mb-1">
              Balloting History
            </label>
            <select
              v-model="filters.has_balloting_3yr"
              class="filter-select"
            >
              <option :value="null">All history</option>
              <option :value="true">Balloted in last 3 years</option>
              <option :value="false">Not balloted in last 3 years</option>
            </select>
          </div>
        </div>

        <!-- Special programme toggles -->
        <label class="block text-xs font-medium text-gray-600 mb-1">Additional Filters</label>
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
              <input type="checkbox" v-model="filters.gifted_ind" />
              <span class="text-sm font-medium text-gray-700">GEP [Gifted Education Programme]</span>
            </div>
            <span class="text-xs text-gray-400 leading-snug">For students identified as gifted in P3</span>
          </label>
          <label class="flex flex-col gap-0.5 cursor-pointer select-none">
            <div class="flex items-center gap-1.5">
              <input type="checkbox" v-model="filters.autonomous_ind" />
              <span class="text-sm font-medium text-gray-700">Autonomous</span>
            </div>
            <span class="text-xs text-gray-400 leading-snug">Flexibility to introduce special programmes</span>
          </label>
          <!-- <label class="flex flex-col gap-0.5 cursor-pointer select-none">
            <div class="flex items-center gap-1.5">
              <input type="checkbox" v-model="filters.ip_ind" />
              <span class="text-sm font-medium text-gray-700">IP</span>
            </div>
            <span class="text-xs text-gray-400 leading-snug">6-year through-train to JC, skipping O-levels</span>
          </label> -->
        </div>

        <div v-if="validationError" class="text-xs text-red-500 mb-3">{{ validationError }}</div>

        <div class="flex gap-3">
          <button @click="fetchRecommendations" :disabled="loading"
            class="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg
                   hover:bg-blue-700 disabled:opacity-50 transition-colors">
            {{ loading ? 'Searching...' : 'Search' }}
          </button>
          <button @click="resetFilters"
            class="px-5 py-2 bg-white border border-gray-300 text-gray-600 text-sm
                   font-medium rounded-lg hover:bg-gray-50 transition-colors">
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

    <!-- Legend + results header -->
    <div v-if="searched && !loading && results.length > 0">

      <!-- Legend — always visible, 2-col layout on all screen sizes -->
      <div class="bg-blue-50 border border-blue-100 rounded-xl p-4 mb-4">
        <p class="text-sm font-semibold text-blue-800 mb-3">Ballot Risk Levels</p>
        <div class="grid grid-cols-1 gap-2">
          <div class="flex items-start gap-3">
            <span class="badge bg-gray-300 text-gray-900 shrink-0 w-16 text-center">N/A</span>
            <p class="text-xs text-blue-700 leading-snug">
              Balloting is not applicable. Phase was not opened — all places were filled in earlier phases.
            </p>
          </div>
          <div class="flex items-start gap-3">
            <span class="badge bg-red-100 text-red-700 shrink-0 w-16 text-center">HIGH</span>
            <p class="text-xs text-blue-700 leading-snug">
              Balloted in all 3 of the last 3 years with average subscription rate above 1.2×. Competition is intense.
            </p>
          </div>
          <div class="flex items-start gap-3">
            <span class="badge bg-amber-100 text-amber-700 shrink-0 w-16 text-center">MEDIUM</span>
            <p class="text-xs text-blue-700 leading-snug">
              Balloted in at least 1 of the last 3 years with subscription rate above 1.2×. Monitor closely.
            </p>
          </div>
          <div class="flex items-start gap-3">
            <span class="badge bg-green-100 text-green-700 shrink-0 w-16 text-center">LOW</span>
            <p class="text-xs text-blue-700 leading-snug">
              No balloting in the last 3 years. Vacancies available without balloting based on recent trends.
            </p>
          </div>
        </div>
      </div>

      <!-- Results header -->
      <h2 class="text-lg font-bold text-gray-800 mb-4">
        {{ results.length }} School{{ results.length !== 1 ? 's' : '' }} Found
        <span class="text-m font-normal text-gray-900 ml-2">
          <span v-if="filters.phase">[Phase {{ filters.phase }} · Last 3 Years]</span>
          <span v-else>[Most Recent Year Per Phase]</span>
        </span>
      </h2>
    </div>

    <!-- ── MODE 1 results ── -->
    <div v-if="mode === 1 && results.length > 0" class="grid grid-cols-1 gap-5">
      <div v-for="school in results" :key="school.school_name"
        class="bg-white rounded-xl border border-gray-200 shadow-sm p-5">

        <!-- School header -->
        <div class="flex items-start justify-between gap-3 mb-4">
          <div>
            <h3 class="font-semibold text-gray-900">{{ school.school_name }}</h3>
            <p class="text-xs text-gray-400 mt-0.5">
              {{ [school.zone_code, school.dgp_code].filter(Boolean).join(' · ') }}
            </p>
          </div>
          <div class="flex gap-2 shrink-0 flex-wrap justify-end">
            <span v-if="school.school_attributes?.sap_ind" class="badge bg-amber-50 text-amber-700">SAP</span>
            <span v-if="school.school_attributes?.gifted_ind" class="badge bg-indigo-50 text-indigo-700">GEP</span>
            <span v-if="school.school_attributes?.autonomous_ind" class="badge bg-purple-50 text-purple-700">Autonomous</span>
            <!-- <span v-if="school.school_attributes?.ip_ind" class="badge bg-teal-50 text-teal-700">IP</span> -->
          </div>
        </div>

        <!-- Phase rows -->
        <div class="divide-y divide-gray-200">
          <div v-for="phaseData in school.phases" :key="phaseData.phase" class="py-3 first:pt-0">

            <p class="text-xs font-bold text-gray-900 uppercase tracking-wide mb-2">
              Phase {{ phaseData.phase }}
            </p>

            <!-- Phase 3 — international students only -->
            <template v-if="phaseData.phase === '3'">
              <template v-if="isPhaseOpened(phaseData.years[0])">                
                <!-- Desktop -->
                <div class="hidden sm:grid sm:grid-cols-5 sm:gap-2 sm:text-center mb-2">
                  <div>
                    <p class="text-xs text-gray-400 mb-0.5">Vacancy</p>
                    <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">
                      {{ phaseData.years[0]?.vacancy || 'N/A' }}
                    </p>
                  </div>
                </div>

                <!-- Mobile 3×2 -->
                <div class="sm:hidden mb-2">
                  <div class="grid grid-cols-3 gap-2 mb-2">
                    <div class="text-center">
                      <p class="text-xs text-gray-400 mb-0.5 leading-tight">Vacancy</p>
                      <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">
                        {{ phaseData.years[0]?.vacancy || 'N/A' }}
                      </p>
                    </div>
                  </div>
                </div>
                
                <p class="text-xs text-gray-400 italic">
                  Only international students may apply. Places offered only if vacancies remain after all earlier phases.
                </p>
              </template>

              <template v-else>
                <p class="text-xs text-gray-700">Phase {{ phaseData.phase }} was not opened</p>
              </template>
            </template>

            <!-- Phases 2B, 2C, 2C(S) -->
            <template v-else>
              <template v-if="isPhaseOpened(phaseData.years[0])">

                <!-- Desktop -->
                <div class="hidden sm:grid sm:grid-cols-5 sm:gap-2 sm:text-center mb-2">
                  <div>
                    <p class="text-xs text-gray-400 mb-0.5">Vacancy</p>
                    <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">
                      {{ phaseData.years[0]?.vacancy || 'N/A' }}
                    </p>
                  </div>
                  <div>
                    <p class="text-xs text-gray-400 mb-0.5">Applied</p>
                    <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">
                      {{ phaseData.years[0]?.applied ?? '—' }}
                    </p>
                  </div>
                  <div>
                    <p class="text-xs text-gray-400 mb-0.5">Taken</p>
                    <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">
                      {{ phaseData.years[0]?.taken ?? '—' }}
                    </p>
                  </div>
                  <div>
                    <p class="text-xs text-gray-400 mb-0.5">Subscription Rate</p>
                    <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">
                      {{ phaseData.years[0]?.subscription_rate != null
                        ? phaseData.years[0].subscription_rate.toFixed(2) + 'x' : '—' }}
                    </p>
                  </div>
                  <div>
                    <p class="text-xs text-gray-400 mb-0.5">Ballot Risk</p>
                    <div class="flex justify-center mt-0.5">
                      <RiskBadge :level="phaseData.years[0]?.ballot_risk_level" />
                    </div>
                  </div>
                </div>

                <!-- Mobile 3×2 -->
                <div class="sm:hidden mb-2">
                  <div class="grid grid-cols-3 gap-2 mb-2">
                    <div class="text-center">
                      <p class="text-xs text-gray-400 mb-0.5 leading-tight">Vacancy</p>
                      <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">
                        {{ phaseData.years[0]?.vacancy || 'N/A' }}
                      </p>
                    </div>
                    <div class="text-center">
                      <p class="text-xs text-gray-400 mb-0.5 leading-tight">Applied</p>
                      <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">
                        {{ phaseData.years[0]?.applied ?? '—' }}
                      </p>
                    </div>
                    <div class="text-center">
                      <p class="text-xs text-gray-400 mb-0.5 leading-tight">Taken</p>
                      <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">
                        {{ phaseData.years[0]?.taken ?? '—' }}
                      </p>
                    </div>
                  </div>
                  <div class="grid grid-cols-3 gap-2">
                    <div class="text-center">
                      <p class="text-xs text-gray-400 mb-0.5 leading-tight">Subscription Rate</p>
                      <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">
                        {{ phaseData.years[0]?.subscription_rate != null
                          ? phaseData.years[0].subscription_rate.toFixed(2) + 'x' : '—' }}
                      </p>
                    </div>
                    <div class="text-center">
                      <p class="text-xs text-gray-400 mb-0.5 leading-tight">Ballot Risk</p>
                      <div class="flex justify-center mt-0.5">
                        <RiskBadge :level="phaseData.years[0]?.ballot_risk_level" />
                      </div>
                    </div>
                    <div></div>
                  </div>
                </div>

                <!-- Ballot details -->
                <div v-if="phaseData.years[0]?.ballot_scenario_code"
                  class="mt-2 bg-amber-50 border border-amber-100 rounded-lg p-3">
                  <p class="text-xs font-medium text-amber-800 mb-1">Balloting Conducted For: {{ phaseData.years[0]?.ballot_description ?? '—' }}</p>
                  <!-- <p class="text-xs text-amber-700">
                    Conducted For: {{ phaseData.years[0]?.ballot_description ?? '—' }}
                  </p> -->
                  <template v-if="phaseData.years[0]?.ballot_chance_pct != null">
                    <div class="grid grid-cols-1 gap-0.5 sm:grid-cols-3 mt-0.5">
                      <p class="text-xs text-amber-700">
                        Vacancies For Ballot: {{ phaseData.years[0]?.ballot_vacancies ?? '—' }}
                      </p>
                      <p class="text-xs text-amber-700">
                        Balloting Applicants: {{ phaseData.years[0]?.ballot_applicants ?? '—' }}
                      </p>
                      <p class="text-xs text-amber-700">
                        Balloting Chance: {{ phaseData.years[0].ballot_chance_pct }}%
                      </p>
                    </div>
                  </template>
                </div>

              </template>

              <!-- Phase not opened -->
              <template v-else>
                <div class="flex items-center justify-between">
                  <p class="text-xs text-gray-700">Phase {{ phaseData.phase }} was not opened</p>
                  <!-- <span class="badge bg-gray-100 text-gray-400">N/A</span> -->
                </div>
              </template>
            </template>

          </div>
        </div>

        <p class="text-xs text-gray-700 italic mt-3">
          Based on {{ mostRecentYear(school.phases) }} registration data
        </p>
      </div>
    </div>

    <!-- ── MODE 2 results ── -->
    <div v-if="mode === 2 && results.length > 0" class="grid grid-cols-1 gap-5">
      <div v-for="school in results" :key="school.school_name"
        class="bg-white rounded-xl border border-gray-200 shadow-sm p-5">

        <!-- School header -->
        <div class="flex items-start justify-between gap-3 mb-4">
          <div>
            <h3 class="font-semibold text-gray-900">{{ school.school_name }}</h3>
            <p class="text-xs text-gray-400 mt-0.5">
              {{ [school.zone_code, school.dgp_code].filter(Boolean).join(' · ') }}
            </p>
          </div>
          <div class="flex gap-2 shrink-0 flex-wrap justify-end">
            <span v-if="school.school_attributes?.sap_ind" class="badge bg-amber-50 text-amber-700">SAP</span>
            <span v-if="school.school_attributes?.gifted_ind" class="badge bg-indigo-50 text-indigo-700">GEP</span>
            <span v-if="school.school_attributes?.autonomous_ind" class="badge bg-purple-50 text-purple-700">Autonomous</span>
            <!-- <span v-if="school.school_attributes?.ip_ind" class="badge bg-teal-50 text-teal-700">IP</span> -->
          </div>
        </div>

        <template v-if="isPhaseOpened(school.latest_year)">    
          <!-- Stat boxes -->
          <div class="mb-4">
            <!-- Risk box — full width -->
            <div class="rounded-lg p-3 mb-3 text-center"
              :class="riskBoxClass(school.latest_year?.ballot_risk_level)">
              <p class="text-xs font-medium mb-1"
                :class="riskLabelClass(school.latest_year?.ballot_risk_level)">
                Ballot Risk Level
              </p>
              <p class="text-lg font-bold"
                :class="riskLabelClass(school.latest_year?.ballot_risk_level)">
                {{ school.latest_year?.ballot_risk_level ?? '—' }}
              </p>
            </div>

            <!-- 3 stat boxes in 2-column grid (3rd wraps to new row) -->
            <div class="grid grid-cols-3 gap-2">
              <div class="bg-gray-50 rounded-lg p-3 text-center">
                <p class="text-xs text-gray-400 mb-1">Average Subscription Rate</p>
                <p class="text-sm font-semibold text-gray-800">
                  {{ school.trend?.subscription_rate_3yr_avg
                    ? school.trend.subscription_rate_3yr_avg.toFixed(2) + 'x' : 'N/A' }}
                </p>
              </div>
              <div class="bg-gray-50 rounded-lg p-3 text-center">
                <p class="text-xs text-gray-400 mb-1">Balloted (Last 3 Years)</p>
                <p class="text-sm font-semibold text-gray-800">
                  {{ school.trend?.ballot_occurrences_last_3yr != null
                    ? school.trend.ballot_occurrences_last_3yr + ' / 3' : '—' }}
                </p>
              </div>
              <div class="bg-gray-50 rounded-lg p-3 text-center">
                <p class="text-xs text-gray-400 mb-1">Vacancy Trend (Year On Year)</p>
                <p class="text-sm font-semibold"
                  :class="vacancyTrendClass(school.trend?.vacancy_yoy_change)">
                  {{ formatVacancyTrend(school.trend?.vacancy_yoy_change) }}
                </p>
              </div>
            </div>
          </div>
        </template>


        <template v-else>
              <!-- Stat boxes -->
          <div class="mb-4">
            <!-- Risk box — full width -->
            <div class="rounded-lg p-3 mb-3 text-center"
              :class="riskBoxClass('N/A')">
              <p class="text-xs font-medium mb-1"
                :class="riskLabelClass('N/A')">
                Ballot Risk Level
              </p>
              <p class="text-lg font-bold"
                :class="riskLabelClass('N/A')">
                {{ 'N/A' }}
              </p>
            </div>
          </div>
        </template>


        <!-- History rows -->
        <div class="divide-y divide-gray-200">
          <div v-for="yr in school.history" :key="yr.registration_year"
            class="py-3 first:pt-0"
            :class="yr.is_current_year ? 'opacity-30' : ''">

            <p class="font-bold text-gray-900 uppercase tracking-wide mb-2">
              {{ yr.registration_year }}
              <span v-if="yr.is_current_year" class="normal-case font-normal">
                (current year — pending data)
              </span>
            </p>

            <template v-if="!yr.is_current_year">
              <!-- <template v-if="yr.vacancy !== 0"> -->
              <!-- Phase 3 history — vacancy only -->
              <template v-if="filters.phase === '3'">
                <template v-if="yr.vacancy > 0">
                  <div class="grid grid-cols-3 gap-2 text-center mb-2">
                    <div>
                      <p class="text-xs text-gray-400 mb-0.5 leading-tight">Vacancy</p>
                      <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">
                        {{ yr.vacancy ?? '—' }}
                      </p>
                    </div>
                  </div>
                  <p class="text-xs text-gray-400 italic">
                    Only international students may apply. Places offered only if vacancies remain after all earlier phases.
                  </p>
                </template>
                
                <!-- Phase not opened -->
                <template v-else>
                  <div class="flex items-center justify-between">
                    <p class="text-xs text-gray-700">Phase {{ school.phase }} was not opened</p>
                    <!-- <span class="badge bg-gray-100 text-gray-400">N/A</span> -->
                  </div>
                </template>
              </template>
              <!-- </template> -->

              <!-- Phases 2B, 2C, 2C(S) history -->
              <template v-else>
                <!-- Desktop -->
                <template v-if="yr.vacancy > 0">
                  <div class="hidden sm:grid sm:grid-cols-6 sm:gap-2 sm:text-center mb-2">
                  <div>
                    <p class="text-xs text-gray-400 mb-0.5">Vacancy</p>
                    <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">{{ yr.vacancy ?? '—' }}</p>
                  </div>
                  <div>
                    <p class="text-xs text-gray-400 mb-0.5">Applied</p>
                    <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">{{ yr.applied ?? '—' }}</p>
                  </div>
                  <div>
                    <p class="text-xs text-gray-400 mb-0.5">Taken</p>
                    <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">{{ yr.taken ?? '—' }}</p>
                  </div>
                  <div>
                    <p class="text-xs text-gray-400 mb-0.5">Subscription Rate</p>
                    <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">
                      {{ yr.subscription_rate ? yr.subscription_rate.toFixed(2) + 'x' : 'N/A' }}
                    </p>
                  </div>
                  <div>
                    <p class="text-xs text-gray-400 mb-0.5">Ballot Conducted</p>
                    <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">
                      {{ yr.ballot_scenario_code ?? 'N/A' }}
                    </p>
                  </div>
                  <div>
                    <p class="text-xs text-gray-400 mb-0.5">Ballot Chance</p>
                    <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">
                      {{ yr.ballot_chance_pct ? yr.ballot_chance_pct + '%' : 'N/A' }}
                    </p>
                  </div>
                </div>

                <!-- Mobile 3×2 -->
                <div class="sm:hidden mb-2">
                  <div class="grid grid-cols-3 gap-2 mb-2">
                    <div class="text-center">
                      <p class="text-xs text-gray-400 mb-0.5 leading-tight">Vacancy</p>
                      <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">{{ yr.vacancy ?? '—' }}</p>
                    </div>
                    <div class="text-center">
                      <p class="text-xs text-gray-400 mb-0.5 leading-tight">Applied</p>
                      <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">{{ yr.applied ?? '—' }}</p>
                    </div>
                    <div class="text-center">
                      <p class="text-xs text-gray-400 mb-0.5 leading-tight">Taken</p>
                      <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">{{ yr.taken ?? '—' }}</p>
                    </div>
                  </div>
                  <div class="grid grid-cols-3 gap-2">
                    <div class="text-center">
                      <p class="text-xs text-gray-400 mb-0.5 leading-tight">Subscription Rate</p>
                      <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">
                        {{ yr.subscription_rate ? yr.subscription_rate.toFixed(2) + 'x' : 'N/A' }}
                      </p>
                    </div>
                    <div class="text-center">
                      <p class="text-xs text-gray-400 mb-0.5 leading-tight">Ballot Conducted</p>
                      <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">
                        {{ yr.ballot_scenario_code ?? 'N/A' }}
                      </p>
                    </div>
                    <div class="text-center">
                      <p class="text-xs text-gray-400 mb-0.5 leading-tight">Ballot Chance</p>
                      <p class="text-sm font-semibold text-gray-800 whitespace-nowrap">
                        {{ yr.ballot_chance_pct ? yr.ballot_chance_pct + '%' : 'N/A' }}
                      </p>
                    </div>
                  </div>
                </div>

                <!-- Ballot details -->
                <div v-if="yr.ballot_scenario_code"
                  class="mt-2 bg-amber-50 border border-amber-100 rounded-lg p-3">
                  <p class="text-xs font-medium text-amber-800 mb-1">Balloting Conducted For: {{ yr.ballot_description ?? '—' }}</p>
                  <!-- <p class="text-xs text-amber-700">
                    Conducted For: {{ yr.ballot_description ?? '—' }}
                  </p> -->
                  <template v-if="yr.ballot_chance_pct != null">
                    <div class="grid grid-cols-1 gap-0.5 sm:grid-cols-3 mt-0.5">
                      <p class="text-xs text-amber-700">
                        Vacancies For Ballot: {{ yr.ballot_vacancies ?? '—' }}
                      </p>
                      <p class="text-xs text-amber-700">
                        Balloting Applicants: {{ yr.ballot_applicants ?? '—' }}
                      </p>
                      <p class="text-xs text-amber-700">
                        Balloting Chance: {{ yr.ballot_chance_pct }}%
                      </p>
                    </div>
                  </template>
                  
                  <template v-else>
                    <p class="text-xs italic text-amber-700">Balloting details were not released pre-2024</p>
                  </template>
                </div>
                </template>
                
                <!-- Phase not opened -->
                <template v-else>
                  <div class="flex items-center justify-between">
                    <p class="text-xs text-gray-700">Phase {{ school.phase }} was not opened</p>
                    <!-- <span class="badge bg-gray-100 text-gray-400">N/A</span> -->
                  </div>
                </template>

              </template>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="searched && !loading && results.length === 0"
      class="text-center py-16 text-gray-400">
      <p class="text-lg mb-1">No schools found</p>
      <p class="text-sm">Try adjusting your filters</p>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import apiClient from '../services/api'
import { metadata, metadataLoading, metadataError } from '../services/metadata'
import RiskBadge from '../components/RiskBadge.vue'

const results = ref([])
const loading = ref(false)
const error = ref(null)
const searched = ref(false)
const mode = ref(0)
const validationError = ref(null)

const filters = reactive({
  zone_code: '', dgp_code: '', type_code: '', nature_code: '',
  phase: '', has_balloting_3yr: null,
  sap_ind: false, autonomous_ind: false, gifted_ind: false, ip_ind: false,
})

const availableEstates = computed(() => {
  if (!metadata.value) return []
  if (!filters.zone_code) return metadata.value.all_estates
  return metadata.value.estates_by_zone[filters.zone_code] ?? []
})

function onZoneChange() { filters.dgp_code = '' }
function onPhaseChange() { if (!filters.phase) filters.has_balloting_3yr = null }

function isPhaseOpened(yearRow) {
  if (!yearRow || yearRow.is_current_year) return false
  return yearRow.vacancy !== null && yearRow.vacancy > 0
}

function mostRecentYear(phases) {
  for (const phase of phases) {
    const nonCurrent = phase.years.find(y => !y.is_current_year)
    if (nonCurrent) return nonCurrent.registration_year
  }
  return '—'
}

function riskBoxClass(level) {
  switch (level) {
    case 'HIGH':   return 'bg-red-100'
    case 'MEDIUM': return 'bg-amber-100'
    case 'LOW':    return 'bg-green-100'
    default:       return 'bg-gray-100'
  }
}

function riskLabelClass(level) {
  switch (level) {
    case 'HIGH':   return 'text-red-700'
    case 'MEDIUM': return 'text-amber-700'
    case 'LOW':    return 'text-green-700'
    default:       return 'text-gray-500'
  }
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

// On mount: apply query params from HomeView deep links
const route = useRoute()

onMounted(() => {
  const q = route.query
  const hasQueryParams = q.zone_code || q.dgp_code || q.phase

  if (hasQueryParams) {
    if (q.zone_code) filters.zone_code = q.zone_code
    if (q.dgp_code) filters.dgp_code = q.dgp_code
    if (q.phase) filters.phase = q.phase
    
    // has_balloting_3yr comes as string 'true'/'false' from URL — convert to boolean
    if (q.has_balloting_3yr === 'true') filters.has_balloting_3yr = true
    if (q.has_balloting_3yr === 'false') filters.has_balloting_3yr = false
    fetchRecommendations()
  }
})
</script>