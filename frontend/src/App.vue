<script setup lang="ts">
import { ClipboardCheckIcon, MenuIcon } from '@lucide/vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import ThemePicker from '@/components/ThemePicker.vue'
import ThemeToggle from '@/components/ThemeToggle.vue'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Toaster } from '@/components/ui/sonner'
import { useTheme } from '@/composables/useTheme'

const { theme, mode } = useTheme()
const route = useRoute()

const links = [
  { to: '/', label: 'Today' },
  { to: '/rooms', label: 'Rooms' },
  { to: '/members', label: 'Members' },
  { to: '/settings', label: 'Settings' },
]

// Today stays lit on per-member checklist pages
function isActive(to: string) {
  if (to === '/') return route.path === '/' || route.path.startsWith('/checklist/')
  return route.path === to || route.path.startsWith(`${to}/`)
}
</script>

<template>
  <div class="flex min-h-screen flex-col bg-background text-foreground">
    <header class="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
      <div class="mx-auto flex h-14 w-full max-w-5xl items-center gap-5 px-4">
        <RouterLink to="/" class="flex shrink-0 items-center gap-2 font-semibold tracking-tight">
          <span
            class="grid size-6 place-items-center rounded-md bg-gradient-to-br from-primary to-primary/60 text-primary-foreground shadow-sm"
          >
            <ClipboardCheckIcon class="size-3.5" />
          </span>
          Chore Tracker
        </RouterLink>
        <nav class="hidden items-center gap-4 text-sm text-muted-foreground md:flex">
          <RouterLink
            v-for="link in links"
            :key="link.to"
            :to="link.to"
            class="relative py-1 whitespace-nowrap transition-colors hover:text-foreground"
            :class="
              isActive(link.to)
                ? 'text-foreground after:absolute after:-bottom-0.5 after:left-0 after:h-0.5 after:w-full after:rounded-full after:bg-primary'
                : ''
            "
          >
            {{ link.label }}
          </RouterLink>
        </nav>
        <div class="ml-auto flex items-center gap-1">
          <ThemePicker />
          <ThemeToggle />
          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <Button variant="ghost" size="icon" class="md:hidden" aria-label="Open navigation">
                <MenuIcon />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" class="w-44">
              <DropdownMenuItem v-for="link in links" :key="link.to" as-child>
                <RouterLink
                  :to="link.to"
                  class="w-full"
                  :class="isActive(link.to) ? 'font-medium' : ''"
                >
                  {{ link.label }}
                  <span
                    v-if="isActive(link.to)"
                    class="ml-auto size-1.5 rounded-full bg-primary"
                    aria-hidden="true"
                  />
                </RouterLink>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
    <main class="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
      <RouterView v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </RouterView>
    </main>
    <footer class="border-t">
      <div
        class="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-4 text-xs text-muted-foreground"
      >
        <span>chore tracker — built from app-template</span>
        <span class="inline-flex items-center gap-1.5" title="current theme">
          <span class="size-1.5 rounded-full bg-primary" />
          {{ theme }} · {{ mode }}
        </span>
      </div>
    </footer>
    <Toaster position="bottom-right" />
  </div>
</template>
