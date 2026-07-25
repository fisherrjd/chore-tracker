<script setup lang="ts">
import { PaletteIcon } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useTheme } from '@/composables/useTheme'
import { THEMES, type ThemeId } from '@/lib/themes'

const { theme, setTheme } = useTheme()
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <Button variant="ghost" size="sm">
        <PaletteIcon />
        {{ THEMES.find((t) => t.id === theme)?.label }}
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end">
      <DropdownMenuRadioGroup
        :model-value="theme"
        @update:model-value="setTheme($event as ThemeId)"
      >
        <DropdownMenuRadioItem v-for="t in THEMES" :key="t.id" :value="t.id">
          {{ t.label }}
        </DropdownMenuRadioItem>
      </DropdownMenuRadioGroup>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
