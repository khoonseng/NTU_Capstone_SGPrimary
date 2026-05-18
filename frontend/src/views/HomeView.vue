<template>
  <div class="flex flex-col items-center justify-center py-20 text-center">
    <h1 class="text-3xl font-bold text-gray-900 mb-4">
      SGPrimary Ballot Insights
    </h1>
    <p class="text-gray-500 text-lg mb-10 max-w-xl">
      Helping Singapore parents make informed Primary 1 school choices
      based on historical ballot data.
    </p>
    <div class="flex gap-4">
      <router-link
        to="/schools"
        class="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
      >
        Browse Schools
      </router-link>
      <router-link
        to="/recommend"
        class="px-6 py-3 bg-white border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors"
      >
        Get Recommendations
      </router-link>
    </div>
  </div>
</template>
