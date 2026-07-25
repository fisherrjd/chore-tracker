import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/rooms', name: 'rooms', component: () => import('@/views/RoomsView.vue') },
    { path: '/members', name: 'members', component: () => import('@/views/MembersView.vue') },
    { path: '/settings', name: 'settings', component: () => import('@/views/SettingsView.vue') },
    {
      path: '/checklist/:member',
      name: 'checklist',
      component: () => import('@/views/ChecklistView.vue'),
    },
  ],
})

export default router
