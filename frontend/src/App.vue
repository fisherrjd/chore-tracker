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
    <header class="border-b border-border bg-card">
      <div class="mx-auto max-w-5xl px-4">
        <div class="flex h-14 items-center gap-6">
          <RouterLink to="/" class="text-base font-semibold text-foreground">
            🧹 Chore Tracker
          </RouterLink>
          <nav class="flex gap-1">
            <RouterLink
              v-for="link in navLinks"
              :key="link.to"
              :to="link.to"
              :class="[
                'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                isActive(link.to)
                  ? 'bg-secondary text-secondary-foreground'
                  : 'text-muted-foreground hover:bg-secondary/60 hover:text-foreground',
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

    <footer class="border-t border-border py-4 text-center text-xs text-muted-foreground">
      Chore Tracker &copy; {{ currentYear }}
    </footer>

    <Toaster position="bottom-right" rich-colors />
  </div>
</template>
