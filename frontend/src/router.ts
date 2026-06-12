import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import RoomsView from '@/views/RoomsView.vue'
import MembersView from '@/views/MembersView.vue'
import SettingsView from '@/views/SettingsView.vue'
import ChecklistView from '@/views/ChecklistView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/rooms', component: RoomsView },
    { path: '/members', component: MembersView },
    { path: '/settings', component: SettingsView },
    { path: '/checklist/:member', component: ChecklistView },
  ],
})

export default router
