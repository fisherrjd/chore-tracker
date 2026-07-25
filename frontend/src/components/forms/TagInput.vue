<script setup lang="ts">
import { PlusIcon, XIcon } from '@lucide/vue'
import { ref } from 'vue'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

// removable-chip editor (tags, emails, times), generalized from
// chore-tracker's notification-times UI. v-model is a string[];
// duplicates are silently dropped.
withDefaults(
  defineProps<{
    placeholder?: string
    /** native input type — "time" gives HH:MM chips with a picker */
    type?: string
    /** monospace chips, for times and codes */
    mono?: boolean
  }>(),
  { placeholder: 'Add…', type: 'text' },
)

const model = defineModel<string[]>({ default: () => [] })
const draft = ref('')

function add() {
  const v = draft.value.trim()
  if (v && !model.value.includes(v)) model.value = [...model.value, v]
  draft.value = ''
}

function remove(v: string) {
  model.value = model.value.filter((x) => x !== v)
}
</script>

<template>
  <div class="space-y-2">
    <div v-if="model.length" class="flex flex-wrap gap-1.5">
      <Badge
        v-for="v in model"
        :key="v"
        variant="secondary"
        class="gap-1 pr-1"
        :class="mono ? 'font-mono' : ''"
      >
        {{ v }}
        <button
          class="rounded-full p-0.5 transition-colors hover:text-destructive"
          :aria-label="`Remove ${v}`"
          @click="remove(v)"
        >
          <XIcon class="size-3" />
        </button>
      </Badge>
    </div>
    <div class="flex gap-2">
      <Input
        v-model="draft"
        :type="type"
        :placeholder="placeholder"
        class="max-w-44"
        @keydown.enter.prevent="add"
      />
      <Button
        variant="secondary"
        size="icon"
        :disabled="!draft.trim()"
        aria-label="Add"
        @click="add"
      >
        <PlusIcon />
      </Button>
    </div>
  </div>
</template>
