<script setup lang="ts">
import { MoonIcon, SunIcon } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { useTheme } from '@/composables/useTheme'

const { mode, toggleMode } = useTheme()
</script>

<template>
  <Button variant="ghost" size="icon" aria-label="Toggle dark mode" @click="toggleMode">
    <MoonIcon v-if="mode === 'light'" />
    <SunIcon v-else />
  </Button>
</template>
