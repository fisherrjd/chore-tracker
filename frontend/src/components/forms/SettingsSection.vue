<script setup lang="ts">
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

// one titled card per settings concern; put save/cancel in #footer.
defineProps<{
  title: string
  description?: string
}>()
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>{{ title }}</CardTitle>
      <CardDescription v-if="description">{{ description }}</CardDescription>
    </CardHeader>
    <CardContent class="space-y-4">
      <slot />
    </CardContent>
    <CardFooter v-if="$slots.footer" class="justify-end gap-2 border-t">
      <slot name="footer" />
    </CardFooter>
  </Card>
</template>
