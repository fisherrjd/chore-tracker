<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { Toaster } from 'vue-sonner'
import { computed } from 'vue'

const route = useRoute()

const navLinks = [
  { to: '/', label: 'Home' },
  { to: '/rooms', label: 'Rooms' },
  { to: '/members', label: 'Members' },
  { to: '/settings', label: 'Settings' },
]

function isActive(path: string) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

const currentYear = computed(() => new Date().getFullYear())
</script>

<template>
  <div class="min-h-screen bg-background">
    <header class="bg-primary text-primary-foreground shadow-sm">
      <div class="mx-auto max-w-5xl px-4">
        <div class="flex min-h-14 flex-wrap items-center gap-x-6 gap-y-2 py-2">
          <RouterLink to="/" class="text-base font-semibold text-primary-foreground">
            🧹 Chore Tracker
          </RouterLink>
          <nav class="flex flex-wrap gap-1">
            <RouterLink
              v-for="link in navLinks"
              :key="link.to"
              :to="link.to"
              :class="[
                'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                isActive(link.to)
                  ? 'bg-primary-foreground/15 text-primary-foreground'
                  : 'text-primary-foreground/70 hover:bg-primary-foreground/10 hover:text-primary-foreground',
              ]"
            >
              {{ link.label }}
            </RouterLink>
          </nav>
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-5xl px-4 py-8">
      <RouterView />
    </main>

    <footer class="border-t-2 border-primary/30 py-4 text-center text-xs text-muted-foreground">
      Chore Tracker &copy; {{ currentYear }}
    </footer>

    <Toaster position="bottom-right" rich-colors />
  </div>
</template>
