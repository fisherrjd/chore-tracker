<script setup lang="ts">
import type { Component } from 'vue'
import { InboxIcon } from '@lucide/vue'

// dashed placeholder for "nothing here yet" — pair with an #action
// button that creates the first thing.
defineProps<{
  title: string
  description?: string
  icon?: Component
}>()
</script>

<template>
  <div
    class="flex flex-col items-center justify-center gap-1 rounded-xl border border-dashed px-6 py-12 text-center"
  >
    <component :is="icon ?? InboxIcon" class="size-8 text-muted-foreground/60" />
    <p class="mt-3 text-sm font-medium">{{ title }}</p>
    <p v-if="description" class="max-w-sm text-sm text-muted-foreground">{{ description }}</p>
    <div v-if="$slots.action" class="mt-3">
      <slot name="action" />
    </div>
  </div>
</template>
