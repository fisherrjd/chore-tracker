<script setup lang="ts">
import { AppShell, type NavSection } from '@fisherrjd/ui/layout'
import {
  CalendarCheckIcon,
  ClipboardCheckIcon,
  DoorOpenIcon,
  PaletteIcon,
  SettingsIcon,
  ShoppingCartIcon,
  UsersIcon,
} from '@lucide/vue'
import { RouterView } from 'vue-router'

const nav: NavSection[] = [
  {
    label: 'Household',
    links: [
      { to: '/', label: 'Today', icon: CalendarCheckIcon },
      { to: '/lists', label: 'Lists', icon: ShoppingCartIcon },
    ],
  },
  {
    label: 'Setup',
    links: [
      { to: '/rooms', label: 'Rooms', icon: DoorOpenIcon },
      { to: '/members', label: 'Members', icon: UsersIcon },
      { to: '/settings', label: 'Settings', icon: SettingsIcon },
      // dev only, like its route (src/router.ts)
      ...(import.meta.env.DEV ? [{ to: '/styleguide', label: 'Styleguide', icon: PaletteIcon }] : []),
    ],
  },
]
</script>

<template>
  <AppShell brand="chores" :icon="ClipboardCheckIcon" :nav="nav">
    <RouterView v-slot="{ Component }">
      <Transition name="page" mode="out-in">
        <component :is="Component" />
      </Transition>
    </RouterView>
  </AppShell>
</template>
