<script setup lang="ts">
import { computed, useId } from 'vue'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'

// checkbox list with strike-through and a progress count, generalized
// from chore-tracker. the parent owns `done` (v-model:done), so
// persistence — localStorage, debounced API save — is its call.
const props = withDefaults(
  defineProps<{
    items: { id: string; label: string }[]
    /** show the n/m counter above the list */
    progress?: boolean
  }>(),
  { progress: true },
)

const done = defineModel<string[]>('done', { default: () => [] })

const uid = useId()

function toggle(id: string, checked: boolean) {
  const set = new Set(done.value)
  if (checked) set.add(id)
  else set.delete(id)
  done.value = [...set]
}

const count = computed(() => props.items.filter((i) => done.value.includes(i.id)).length)
</script>

<template>
  <div class="space-y-3">
    <p v-if="progress" class="text-xs text-muted-foreground tabular-nums">
      {{ count }}/{{ items.length }} done
    </p>
    <div v-for="item in items" :key="item.id" class="flex items-center gap-3">
      <Checkbox
        :id="`${uid}-${item.id}`"
        :model-value="done.includes(item.id)"
        @update:model-value="(v) => toggle(item.id, v === true)"
      />
      <Label
        :for="`${uid}-${item.id}`"
        class="cursor-pointer font-normal"
        :class="done.includes(item.id) ? 'text-muted-foreground line-through' : ''"
      >
        {{ item.label }}
      </Label>
    </div>
  </div>
</template>
