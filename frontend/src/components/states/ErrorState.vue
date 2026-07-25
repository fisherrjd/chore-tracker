<script setup lang="ts">
import { TriangleAlertIcon } from '@lucide/vue'
import { Button } from '@/components/ui/button'

// failure placeholder with a retry affordance; override #action to
// replace the default retry button.
withDefaults(
  defineProps<{
    title?: string
    description?: string
    retryLabel?: string
  }>(),
  { title: 'Something went wrong', retryLabel: 'Try again' },
)

const emit = defineEmits<{ retry: [] }>()
</script>

<template>
  <div
    class="flex flex-col items-center justify-center gap-1 rounded-xl border border-dashed border-destructive/40 px-6 py-12 text-center"
  >
    <TriangleAlertIcon class="size-8 text-destructive/70" />
    <p class="mt-3 text-sm font-medium">{{ title }}</p>
    <p v-if="description" class="max-w-sm text-sm text-muted-foreground">{{ description }}</p>
    <div class="mt-3">
      <slot name="action">
        <Button variant="outline" size="sm" @click="emit('retry')">{{ retryLabel }}</Button>
      </slot>
    </div>
  </div>
</template>
