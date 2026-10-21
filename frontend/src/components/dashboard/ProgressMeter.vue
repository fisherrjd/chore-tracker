<script setup lang="ts">
defineProps<{
  label: string
  /** 0–100 */
  value: number
  /** right-aligned text; defaults to the percentage */
  detail?: string
}>()
</script>

<template>
  <div class="space-y-1.5">
    <div class="flex items-baseline justify-between gap-2">
      <span class="text-sm font-medium">{{ label }}</span>
      <span class="text-xs text-muted-foreground">{{ detail ?? `${value}%` }}</span>
    </div>
    <div class="h-2 overflow-hidden rounded-full bg-muted">
      <div
        class="h-full rounded-full bg-primary transition-[width] duration-500"
        :style="{ width: `${Math.min(Math.max(value, 0), 100)}%` }"
      />
    </div>
  </div>
</template>
