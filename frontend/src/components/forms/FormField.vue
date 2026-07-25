<script setup lang="ts">
import { useId } from 'vue'
import { Label } from '@/components/ui/label'

// label + control + hint/error in one. bind the slotted control to the
// provided id so the label focuses it:
//   <FormField label="Name" :error="err"  v-slot="{ id }">
//     <Input :id="id" v-model="name" />
//   </FormField>
defineProps<{
  label: string
  hint?: string
  error?: string
  required?: boolean
}>()

const id = useId()
</script>

<template>
  <div class="space-y-2">
    <Label :for="id">
      {{ label }}
      <span v-if="required" aria-hidden="true" class="-ml-1 text-destructive">*</span>
    </Label>
    <slot :id="id" :invalid="!!error" />
    <p v-if="error" class="text-xs font-medium text-destructive">{{ error }}</p>
    <p v-else-if="hint" class="text-xs text-muted-foreground">{{ hint }}</p>
  </div>
</template>
