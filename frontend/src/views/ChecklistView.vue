<script setup lang="ts">
import { Button } from '@fisherrjd/ui/button'
import { Card } from '@fisherrjd/ui/card'
import { PageHeader } from '@fisherrjd/ui/layout'
import { Skeleton } from '@fisherrjd/ui/skeleton'
import { ErrorState } from '@fisherrjd/ui/states'
import { ArrowLeftIcon } from '@lucide/vue'
import { useDebounceFn } from '@vueuse/core'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { toast } from 'vue-sonner'
import Checklist from '@/components/project/Checklist.vue'
import SaveIndicator from '@/components/project/SaveIndicator.vue'
import { api, ApiError } from '@/lib/api'
import type { ChecklistData, ChecklistRoom } from '@/types'

const route = useRoute()
const member = route.params.member as string

const data = ref<ChecklistData | null>(null)
const done = ref<Record<string, string[]>>({})
const notFound = ref(false)
const saveState = ref<'saved' | 'saving' | 'error'>('saved')

function doneByRoom(rooms: ChecklistRoom[]) {
  return Object.fromEntries(rooms.map((r) => [r.name, r.done]))
}

// suppress the save watcher while load() seeds `done`
let seeding = false

async function load() {
  try {
    const result = await api.checklist(member)
    data.value = result
    seeding = true
    done.value = doneByRoom(result.rooms)
    await nextTick()
    seeding = false
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound.value = true
    else toast.error('Failed to load checklist')
  }
}

const save = useDebounceFn(async () => {
  try {
    const res = await api.updateChecklistRooms(member, done.value)
    saveState.value = 'saved'
    const shown = (data.value?.rooms ?? []).map((r) => r.name).join('\n')
    if (data.value && res.rooms.map((r) => r.name).join('\n') !== shown) {
      // mode was switched elsewhere: show what today's rooms really are
      seeding = true
      data.value = {
        ...data.value,
        full_clean: res.full_clean,
        rooms: res.rooms,
        room_name: res.rooms[0]?.name ?? null,
        tasks: res.rooms[0]?.tasks ?? [],
      }
      done.value = doneByRoom(res.rooms)
      await nextTick()
      seeding = false
      toast("Today's rooms changed")
    }
  } catch {
    saveState.value = 'error'
  }
}, 400)

watch(
  done,
  () => {
    if (seeding || !data.value) return
    saveState.value = 'saving'
    void save()
  },
  { deep: true },
)

const items = (tasks: string[]) => tasks.map((t) => ({ id: t, label: t }))

const totals = computed(() => {
  const rooms = data.value?.rooms ?? []
  return {
    done: rooms.reduce((n, r) => n + r.tasks.filter((t) => done.value[r.name]?.includes(t)).length, 0),
    total: rooms.reduce((n, r) => n + r.tasks.length, 0),
  }
})

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-md space-y-6">
    <RouterLink
      to="/"
      class="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
    >
      <ArrowLeftIcon class="size-4" />
      Today
    </RouterLink>

    <ErrorState
      v-if="notFound"
      title="Member not found"
      :description="`Nobody here is called ${member}.`"
    >
      <template #action>
        <Button variant="outline" size="sm" as-child>
          <RouterLink to="/">Back to Today</RouterLink>
        </Button>
      </template>
    </ErrorState>

    <div v-else-if="!data" class="space-y-4">
      <Skeleton class="h-9 w-56" />
      <Skeleton class="h-48 w-full" />
    </div>

    <template v-else>
      <PageHeader
        :title="`${member}'s checklist`"
        :description="
          data.full_clean
            ? `Full house clean · ${data.rooms.length} rooms`
            : `Today's room: ${data.room_name ?? 'none assigned'}`
        "
      >
        <template #actions>
          <SaveIndicator :state="saveState" />
        </template>
      </PageHeader>

      <template v-if="data.full_clean">
        <p class="text-sm text-muted-foreground tabular-nums">
          {{ totals.done }}/{{ totals.total }} done across all rooms
        </p>
        <Card v-for="room in data.rooms" :key="room.name" class="space-y-3 p-5">
          <h2 class="font-semibold">{{ room.name }}</h2>
          <Checklist
            v-if="room.tasks.length"
            v-model:done="done[room.name]"
            :items="items(room.tasks)"
          />
          <p v-else class="text-sm text-muted-foreground">No tasks for this room.</p>
        </Card>
      </template>

      <Card v-else class="p-5">
        <Checklist
          v-if="data.rooms.length && data.rooms[0].tasks.length"
          v-model:done="done[data.rooms[0].name]"
          :items="items(data.rooms[0].tasks)"
        />
        <p v-else class="text-sm text-muted-foreground">No tasks for this room.</p>
      </Card>
    </template>
  </div>
</template>
