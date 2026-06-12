<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { toast } from 'vue-sonner'
import { useDebounceFn } from '@vueuse/core'
import { api, ApiError } from '@/lib/api'
import type { ChecklistData } from '@/types'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

const route = useRoute()
const member = route.params.member as string

const data = ref<ChecklistData | null>(null)
const done = ref<Set<string>>(new Set())
const notFound = ref(false)

async function load() {
  try {
    const result = await api.checklist(member)
    data.value = result
    done.value = new Set(result.done)
  } catch (e: unknown) {
    if (e instanceof ApiError && e.status === 404) notFound.value = true
    else toast.error('Failed to load checklist')
  }
}

const save = useDebounceFn(async () => {
  try {
    await api.updateChecklist(member, [...done.value])
  } catch {
    toast.error('Failed to save')
  }
}, 400)

function toggle(task: string, checked: boolean) {
  if (checked) done.value.add(task)
  else done.value.delete(task)
  void save()
}

onMounted(load)
</script>

<template>
  <div v-if="notFound" class="text-muted-foreground">
    Member <strong>{{ member }}</strong> not found.
  </div>

  <div v-else-if="!data" class="text-muted-foreground">Loading…</div>

  <div v-else class="max-w-md space-y-4">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">{{ member }}'s Checklist</h1>
      <p class="text-sm text-muted-foreground">
        Today's room:
        <span class="font-medium text-foreground">{{ data.room_name ?? 'None assigned' }}</span>
      </p>
    </div>

    <div class="flex gap-2">
      <Badge variant="secondary">
        {{ done.size }}/{{ data.tasks.length }} done
      </Badge>
    </div>

    <Card>
      <CardHeader class="pb-3">
        <CardTitle class="text-base">Tasks</CardTitle>
        <CardDescription v-if="!data.tasks.length">No tasks for this room.</CardDescription>
      </CardHeader>
      <CardContent class="space-y-3">
        <div
          v-for="task in data.tasks"
          :key="task"
          class="flex items-center gap-3"
        >
          <Checkbox
            :id="`task-${task}`"
            :checked="done.has(task)"
            @update:checked="(v) => toggle(task, v)"
          />
          <Label
            :for="`task-${task}`"
            :class="['cursor-pointer', done.has(task) ? 'line-through text-muted-foreground' : '']"
          >
            {{ task }}
          </Label>
        </div>
      </CardContent>
    </Card>
  </div>
</template>
