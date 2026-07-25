<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>

<template>
  <div class="flex flex-wrap items-center justify-between gap-4">
    <div class="space-y-1">
      <h1
        class="bg-gradient-to-r from-foreground to-foreground/60 bg-clip-text text-3xl font-bold tracking-tight text-transparent"
      >
        {{ title }}
      </h1>
      <p v-if="description" class="text-muted-foreground">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="flex flex-wrap items-center gap-2">
      <slot name="actions" />
    </div>
  </div>
</template>
