<script setup lang="ts">
import { SendIcon } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { toast } from 'vue-sonner'
import PageHeader from '@/components/PageHeader.vue'
import ProgressMeter from '@/components/dashboard/ProgressMeter.vue'
import UserAvatar from '@/components/dashboard/UserAvatar.vue'
import EmptyState from '@/components/states/EmptyState.vue'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { api } from '@/lib/api'
import type { HomeData } from '@/types'

const data = ref<HomeData | null>(null)
const loading = ref(true)
const sending = ref(false)

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

function formatDate(iso: string) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
}

const people = computed(() => Object.keys(data.value?.schedule[0]?.assignments ?? {}))

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
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <RouterLink
          v-for="(room, person, i) in data.schedule[0]!.assignments"
          :key="person"
          :to="`/checklist/${person}`"
          class="rise-in block h-full"
          :style="{ animationDelay: `${i * 60}ms` }"
        >
          <Card class="card-hover h-full gap-3 p-5">
            <div class="flex items-center gap-3">
              <UserAvatar :name="String(person)" size="lg" />
              <div class="min-w-0">
                <CardTitle class="truncate text-base">{{ person }}</CardTitle>
                <CardDescription>{{ room }}</CardDescription>
              </div>
            </div>
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
                <TableHead v-for="person in people" :key="person">{{ person }}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow
                v-for="(day, i) in data.schedule"
                :key="day.date"
                :class="i === 0 ? 'bg-accent/40 font-medium' : ''"
              >
                <TableCell class="whitespace-nowrap">{{ formatDate(day.date) }}</TableCell>
                <TableCell v-for="person in people" :key="person">
                  {{ day.assignments[person] ?? '—' }}
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
      </Card>
    </template>
  </div>
</template>
