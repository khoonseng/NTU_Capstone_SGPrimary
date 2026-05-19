import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import SchoolsView from '../views/SchoolsView.vue'
import RecommendView from '../views/RecommendView.vue'
import SchoolDetailView from '../views/SchoolDetailView.vue'

const routes = [
  { path: '/', component: HomeView },
  { path: '/schools', component: SchoolsView },
  { path: '/schools/:schoolName', component: SchoolDetailView },
  { path: '/recommend', component: RecommendView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
