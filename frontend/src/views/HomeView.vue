<script setup lang="ts">
import { Button } from '@fisherrjd/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@fisherrjd/ui/card'
import { ProgressMeter } from '@fisherrjd/ui/dashboard'
import { PageHeader } from '@fisherrjd/ui/layout'
import { Skeleton } from '@fisherrjd/ui/skeleton'
import { ConfirmDialog, EmptyState } from '@fisherrjd/ui/states'
import { swatch } from '@fisherrjd/ui/theme'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@fisherrjd/ui/table'
import { SendIcon, SparklesIcon } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { toast } from 'vue-sonner'
import { api, ApiError } from '@/lib/api'
import type { HomeData } from '@/types'

const data = ref<HomeData | null>(null)
const loading = ref(true)
const sending = ref(false)
const fullBusy = ref(false)

async function load() {
  try {
    data.value = await api.home()
  } catch {
    toast.error('Failed to load schedule')
  } finally {
    loading.value = false
  }
}

async function sendNotifications() {
  sending.value = true
  try {
    const result = await api.notifyToday()
    if (result.sent.length) toast.success(`Sent to: ${result.sent.join(', ')}`)
    if (result.failed.length) toast.error(`Failed: ${result.failed.join(', ')}`)
    if (!result.sent.length && !result.failed.length) toast.warning('No assignments to notify')
    await load()
  } catch (e) {
    toast.error(e instanceof Error ? e.message : 'Failed to send notifications')
  } finally {
    sending.value = false
  }
}

async function startFullClean() {
  if (fullBusy.value) return
  fullBusy.value = true
  try {
    const result = await api.startFullClean()
    toast.success('Full house clean started')
    if (result.failed.length) toast.error(`Failed: ${result.failed.join(', ')}`)
    await load()
  } catch (e) {
    toast.error(e instanceof ApiError ? e.message : 'Failed to start full house clean')
  } finally {
    fullBusy.value = false
  }
}

async function stopFullClean() {
  if (fullBusy.value) return
  fullBusy.value = true
  try {
    await api.stopFullClean()
    toast.success('Back to the normal rotation')
    await load()
  } catch (e) {
    toast.error(e instanceof ApiError ? e.message : 'Failed to stop full house clean')
  } finally {
    fullBusy.value = false
  }
}

function formatDate(iso: string) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
}

const people = computed(() => Object.keys(data.value?.schedule[0]?.assignments ?? {}))

// today's rooms per person: the full-clean split when active, else the rotation
const todayRooms = computed<Record<string, string[]>>(() => {
  if (data.value?.full_clean) return data.value.full_clean_rooms
  const out: Record<string, string[]> = {}
  for (const [person, room] of Object.entries(data.value?.schedule[0]?.assignments ?? {})) {
    out[person] = room ? [room] : []
  }
  return out
})

const description = computed(() => {
  if (!data.value?.schedule.length) return 'Nothing scheduled yet.'
  const date = formatDate(data.value.schedule[0]!.date)
  const times = data.value.notify_times.length
    ? ` · notifications at ${data.value.notify_times.join(', ')}`
    : ''
  return `${date}${times}`
})

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <PageHeader title="Today" :description="description">
      <template #actions>
        <ConfirmDialog
          v-if="!data?.full_clean"
          title="Start a full house clean?"
          :description="`Every room is split between ${people.join(' and ')} for today, and everyone gets a notification. Tomorrow the normal rotation is back.`"
          confirm-label="Start full clean"
          @confirm="startFullClean"
        >
          <Button variant="outline" :disabled="fullBusy || loading || !people.length">
            <SparklesIcon />
            Full house clean
          </Button>
        </ConfirmDialog>
        <Button :disabled="sending || loading" @click="sendNotifications">
          <SendIcon />
          {{ sending ? 'Sending…' : 'Send notifications' }}
        </Button>
      </template>
    </PageHeader>

    <div v-if="loading" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <Skeleton v-for="i in 3" :key="i" class="h-32" />
    </div>

    <EmptyState
      v-else-if="!data?.schedule.length"
      title="No schedule yet"
      description="Add rooms and members, and the rotation builds itself."
    >
      <template #action>
        <Button variant="outline" size="sm" as-child>
          <RouterLink to="/rooms">Set up rooms</RouterLink>
        </Button>
      </template>
    </EmptyState>

    <template v-else>
      <Card v-if="data.full_clean" class="rise-in border-warning/40 bg-warning/10 py-4">
        <CardContent class="flex flex-wrap items-center justify-between gap-3 px-5">
          <div>
            <CardTitle>Full house clean today</CardTitle>
            <p class="text-sm text-muted-foreground">
              Every room is split between you. The normal rotation is back tomorrow.
            </p>
          </div>
          <Button variant="outline" :disabled="fullBusy" @click="stopFullClean">Back to normal</Button>
        </CardContent>
      </Card>

      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <RouterLink
          v-for="(rooms, person, i) in todayRooms"
          :key="person"
          :to="`/checklist/${person}`"
          class="rise-in block h-full"
          :style="{ animationDelay: `${i * 60}ms` }"
        >
          <!-- each member gets their own color: the band, and (via --primary) the progress bar -->
          <Card class="card-hover h-full gap-0 overflow-hidden p-0" :style="swatch(i, { primary: true })">
            <div class="flex items-center gap-3 bg-swatch px-5 py-4 text-swatch-foreground">
              <span
                class="grid size-12 shrink-0 place-items-center rounded-full border-2 border-current bg-background/25 font-heading text-xl font-semibold"
                aria-hidden="true"
              >
                {{ String(person).slice(0, 1).toUpperCase() }}
              </span>
              <div class="min-w-0">
                <CardTitle class="truncate text-xl">{{ person }}</CardTitle>
                <p class="truncate font-semibold opacity-85">
                  {{ data.full_clean ? `${rooms.length} rooms` : rooms[0] }}
                </p>
              </div>
            </div>
            <div class="px-5 py-4">
              <ProgressMeter
                v-if="data.done_map[person]"
                label="Progress"
                :value="
                  data.done_map[person]!.total
                    ? (data.done_map[person]!.done / data.done_map[person]!.total) * 100
                    : 0
                "
                :detail="`${data.done_map[person]!.done}/${data.done_map[person]!.total} done`"
              />
              <p v-else class="text-sm text-muted-foreground">No tasks</p>
              <ul v-if="rooms.length" class="mt-3 space-y-0.5 text-sm text-muted-foreground">
                <li v-for="name in rooms" :key="name">{{ name }}</li>
              </ul>
            </div>
          </Card>
        </RouterLink>
      </div>

      <Card class="rise-in gap-3 py-5" style="animation-delay: 240ms">
        <CardHeader class="pb-0">
          <CardTitle>14-day rotation</CardTitle>
          <CardDescription>Who has which room, two weeks out.</CardDescription>
        </CardHeader>
        <div class="px-3">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead v-for="(person, p) in people" :key="person">
                  <span
                    class="inline-block rounded-full bg-swatch px-2.5 py-0.5 font-heading font-semibold text-swatch-foreground"
                    :style="swatch(p)"
                  >
                    {{ person }}
                  </span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow
                v-for="(day, i) in data.schedule"
                :key="day.date"
                :class="i === 0 ? 'bg-accent-fill/30 font-semibold' : ''"
              >
                <TableCell class="whitespace-nowrap">{{ i === 0 ? 'Today' : formatDate(day.date) }}</TableCell>
                <TableCell v-for="(person, p) in people" :key="person">
                  <!-- rooms tinted with their person's color, so each column reads as one -->
                  <div v-if="i === 0 && todayRooms[person]?.length" class="flex flex-wrap gap-1">
                    <span
                      v-for="name in todayRooms[person]"
                      :key="name"
                      class="inline-block rounded-md bg-swatch/20 px-2 py-0.5"
                      :style="swatch(p)"
                    >
                      {{ name }}
                    </span>
                  </div>
                  <span
                    v-else-if="i !== 0 && day.assignments[person]"
                    class="inline-block rounded-md bg-swatch/20 px-2 py-0.5"
                    :style="swatch(p)"
                  >
                    {{ day.assignments[person] }}
                  </span>
                  <span v-else class="text-muted-foreground">—</span>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </Card>
    </template>
  </div>
</template>
