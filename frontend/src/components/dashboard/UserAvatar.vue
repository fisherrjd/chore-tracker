<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    name: string
    size?: 'sm' | 'md' | 'lg'
  }>(),
  { size: 'md' },
)

const initials = computed(() =>
  props.name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]!.toUpperCase())
    .join(''),
)

const sizeClass = {
  sm: 'size-6 text-[10px]',
  md: 'size-8 text-xs',
  lg: 'size-10 text-sm',
}
</script>

<template>
  <span
    class="grid shrink-0 select-none place-items-center rounded-full bg-primary/15 font-medium text-primary"
    :class="sizeClass[size]"
    :title="name"
  >
    {{ initials }}
  </span>
</template>
