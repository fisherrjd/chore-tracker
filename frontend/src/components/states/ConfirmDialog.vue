<script setup lang="ts">
import { ref } from 'vue'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'

// wrap any trigger element; @confirm fires only on the confirm button.
//   <ConfirmDialog destructive title="Delete?" @confirm="doIt">
//     <Button variant="destructive">Delete</Button>
//   </ConfirmDialog>
withDefaults(
  defineProps<{
    title?: string
    description?: string
    confirmLabel?: string
    cancelLabel?: string
    destructive?: boolean
  }>(),
  { title: 'Are you sure?', confirmLabel: 'Confirm', cancelLabel: 'Cancel' },
)

const emit = defineEmits<{ confirm: [] }>()
const open = ref(false)

function confirm() {
  open.value = false
  emit('confirm')
}
</script>

<template>
  <Dialog v-model:open="open">
    <DialogTrigger as-child>
      <slot />
    </DialogTrigger>
    <DialogContent class="sm:max-w-sm">
      <DialogHeader>
        <DialogTitle>{{ title }}</DialogTitle>
        <DialogDescription v-if="description">{{ description }}</DialogDescription>
      </DialogHeader>
      <DialogFooter>
        <Button variant="ghost" @click="open = false">{{ cancelLabel }}</Button>
        <Button :variant="destructive ? 'destructive' : 'default'" @click="confirm">
          {{ confirmLabel }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
