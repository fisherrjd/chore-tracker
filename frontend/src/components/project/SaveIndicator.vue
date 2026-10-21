<script setup lang="ts">
// autosave status line, from atlas's debounced notes save. drive it from
// whatever async write you do: saving → saved | error.
defineProps<{ state: 'saved' | 'saving' | 'error' }>()

const DOT = {
  saved: 'bg-success',
  saving: 'bg-warning animate-pulse',
  error: 'bg-destructive',
}

const LABEL = {
  saved: 'Saved',
  saving: 'Saving…',
  error: 'Save failed',
}
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 text-xs"
    :class="state === 'error' ? 'text-destructive' : 'text-muted-foreground'"
  >
    <span class="size-1.5 rounded-full" :class="DOT[state]" />
    {{ LABEL[state] }}
  </span>
</template>
