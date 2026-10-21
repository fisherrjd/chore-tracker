import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/lists', name: 'lists', component: () => import('@/views/ListsView.vue') },
    { path: '/rooms', name: 'rooms', component: () => import('@/views/RoomsView.vue') },
    { path: '/members', name: 'members', component: () => import('@/views/MembersView.vue') },
    { path: '/settings', name: 'settings', component: () => import('@/views/SettingsView.vue') },
    {
      path: '/checklist/:member',
      name: 'checklist',
      component: () => import('@/views/ChecklistView.vue'),
    },
    // dev only: the styleguide and its theme lab are a workshop, never shipped —
    // in a build this branch is dead code, so the page isn't even bundled
    ...(import.meta.env.DEV
      ? [
          {
            path: '/styleguide',
            name: 'styleguide',
            component: () => import('@fisherrjd/ui/styleguide').then((m) => m.StyleguidePage),
          },
        ]
      : []),
  ],
})

export default router
