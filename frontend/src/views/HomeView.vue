<template>
  <div class="max-w-3xl mx-auto">

    <!-- Hero -->
    <div class="text-center py-10 mb-8">
      <h1 class="text-3xl font-bold text-gray-900 mb-3">
        SGPrimary Ballot Insights
      </h1>
      <p class="text-gray-500 text-base leading-relaxed max-w-xl mx-auto">
        A data-driven tool to help Singapore parents make informed Primary 1
        school choices based on historical P1 balloting data.
      </p>
    </div>

    <!-- What is P1 Balloting? -->
    <div class="bg-blue-50 border border-blue-100 rounded-xl p-5 mb-6">
      <h2 class="text-sm font-semibold text-blue-800 mb-2">What is P1 Balloting?</h2>
      <p class="text-xs text-blue-700 leading-relaxed">
        Singapore's Primary 1 registration is conducted in phases. Each phase prioritises
        children with different connections to a school — siblings, alumni parents, volunteers,
        and so on. When more children apply than there are vacancies in a phase, a ballot
        (computerised lucky draw) is conducted. This app helps you understand which schools
        have historically required balloting and what your chances might be.
      </p>
    </div>

    <!-- Use case cards -->
    <div class="grid grid-cols-1 gap-4 mb-8 sm:grid-cols-3">

      <!-- Use case 1 -->
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
        <div class="text-2xl mb-3">🏫</div>
        <div class="flex items-start justify-between gap-3 mb-3">
          <h3 class="text-sm font-semibold text-gray-900 leading-snug">Explore Schools</h3>
          <router-link to="/schools"
            class="inline-flex shrink-0 items-center justify-center rounded-md bg-indigo-600
                   px-3 py-1.5 text-xs font-medium text-white shadow-sm
                   hover:bg-indigo-700 transition-colors">
            Explore
          </router-link>
        </div>
        <p class="text-xs text-gray-500 leading-relaxed mb-4">
          Browse all active primary schools by zone, estate, type, or special programmes
          (SAP, GEP, Autonomous). View school details including address, transport,
          contact information, and leadership.
        </p>
        <div class="bg-gray-50 rounded-lg p-3 mb-4">
          <p class="text-xs text-gray-400 font-medium mb-1">Example</p>
          <p class="text-xs text-gray-600 leading-snug">
            "Show me all government-aided co-ed schools in Bishan."
          </p>
        </div>
        <router-link
          :to="{ path: '/schools', query: { dgp_code: 'BISHAN', type_code: 'GOVERNMENT-AIDED SCHOOL', nature_code: 'CO-ED SCHOOL' }}"
          class="inline-flex items-center justify-center rounded-md bg-amber-500
                 px-3 py-1.5 text-xs font-medium text-white shadow-sm
                 hover:bg-amber-600 transition-colors">
          Try this example
        </router-link>
      </div>

      <!-- Use case 2 -->
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
        <div class="text-2xl mb-3">📍</div>
        <div class="flex items-start justify-between gap-3 mb-3">
          <h3 class="text-sm font-semibold text-gray-900 leading-snug">Check Ballot Risk by Estate</h3>
          <router-link to="/recommend"
            class="inline-flex shrink-0 items-center justify-center rounded-md bg-indigo-600
                   px-3 py-1.5 text-xs font-medium text-white shadow-sm
                   hover:bg-indigo-700 transition-colors">
            Check
          </router-link>
        </div>
        <p class="text-xs text-gray-500 leading-relaxed mb-4">
          Planning to register at a school near your home or a home you are considering?
          Check ballot risk across schools in a specific estate from the most recent year to understand which
          schools are competitive and which have available places.
        </p>
        <div class="bg-gray-50 rounded-lg p-3 mb-4">
          <p class="text-xs text-gray-400 font-medium mb-1">Example</p>
          <p class="text-xs text-gray-600 leading-snug">
            "In Seng Kang, Nan Chiau is more competitive than Springdale —
            which phase should I target?"
          </p>
        </div>
        <router-link
          :to="{ path: '/recommend', query: { dgp_code: 'SENG KANG' }}"
          class="inline-flex items-center justify-center rounded-md bg-amber-500
                 px-3 py-1.5 text-xs font-medium text-white shadow-sm
                 hover:bg-amber-600 transition-colors">
          Try this example
        </router-link>
      </div>

      <!-- Use case 3 -->
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
        <div class="text-2xl mb-3">🎯</div>
        <div class="flex items-start justify-between gap-3 mb-3">
          <h3 class="text-sm font-semibold text-gray-900 leading-snug">Find Low-Risk Schools</h3>
          <router-link to="/recommend"
            class="inline-flex shrink-0 items-center justify-center rounded-md bg-indigo-600
                   px-3 py-1.5 text-xs font-medium text-white shadow-sm
                   hover:bg-indigo-700 transition-colors">
            Find
          </router-link>
        </div>
        <p class="text-xs text-gray-500 leading-relaxed mb-4">
          Looking for schools in your zone with low ballot risk for a specific phase?
          Filter by phase to see trend data and balloting history across all schools
          in your area — useful for PR families and international families.
        </p>
        <div class="bg-gray-50 rounded-lg p-3 mb-4">
          <p class="text-xs text-gray-400 font-medium mb-1">Example</p>
          <p class="text-xs text-gray-600 leading-snug">
            "As a PR family, show me schools around Ang Mo Kio in Phase 2C
            that have not balloted in the last 3 years."
          </p>
        </div>
        <router-link
          :to="{ path: '/recommend', query: { dgp_code: 'ANG MO KIO', phase: '2C', has_balloting_3yr: 'false' }}"
          class="inline-flex items-center justify-center rounded-md bg-amber-500
                 px-3 py-1.5 text-xs font-medium text-white shadow-sm
                 hover:bg-amber-600 transition-colors">
          Try this example
        </router-link>
      </div>

    </div>

    <!-- Phase coverage notice -->
    <div class="bg-amber-50 border border-amber-100 rounded-xl p-5 mb-8">
      <h2 class="text-sm font-semibold text-amber-800 mb-2">
        ⚠️ Phase Coverage — Phases 2B, 2C, 2C(S), and 3 Only
      </h2>
      <p class="text-xs text-amber-700 leading-relaxed mb-2">
        This app currently covers Phases 2B, 2C, 2C(S), and 3 only.
        Phases 1 and 2A are excluded for the following reasons:
      </p>
      <ul class="text-xs text-amber-700 leading-relaxed list-disc list-inside space-y-1">
        <li>
          MOE did not publish vacancy and applied figures for Phases 1, 2A(1), and 2A(2)
          before 2019, making historical trend analysis incomplete for these phases.
        </li>
        <li>
          MOE merged Phases 2A(1) and 2A(2) into a single Phase 2A from 2022 onwards.
          Data integrity across this structural change is still being reviewed.
        </li>
      </ul>
      <p class="text-xs text-amber-700 leading-relaxed mt-2">
        Phase 1 (siblings) and Phase 2A (alumni, staff, MOE Kindergarten) will be
        considered in a future release once data integrity is confirmed.
      </p>
    </div>

    <!-- Data attribution -->
    <div class="text-center text-xs text-gray-400 pb-8 leading-relaxed">
      <p>
        Balloting data sourced from
        <a href="https://sgschooling.com" target="_blank" rel="noopener"
          class="text-blue-400 hover:underline">sgschooling.com</a>
        (2009–2025), maintained by Junda Ong.
      </p>
      <p class="mt-1">
        School information sourced from
        <a href="https://data.gov.sg" target="_blank" rel="noopener"
          class="text-blue-400 hover:underline">data.gov.sg</a>
        under the Singapore Open Data Licence.
      </p>
      <p class="mt-1">
        Predictions are heuristic assessments based on historical data.
        Always verify with
        <a href="https://www.moe.gov.sg/primary/p1-registration"
          target="_blank" rel="noopener"
          class="text-blue-400 hover:underline">MOE's official P1 registration portal</a>.
      </p>
    </div>

  </div>
</template>
