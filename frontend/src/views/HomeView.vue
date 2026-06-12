<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { toast } from 'vue-sonner'
import { api } from '@/lib/api'
import type { HomeData } from '@/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

const data = ref<HomeData | null>(null)
const sending = ref(false)

async function load() {
  try {
    data.value = await api.home()
  } catch {
    toast.error('Failed to load schedule')
  }
}

async function sendNotifications() {
  sending.value = true
  try {
    const result = await api.notifyToday()
    if (result.sent.length) toast.success(`Sent to: ${result.sent.join(', ')}`)
    if (result.failed.length) toast.error(`Failed: ${result.failed.join(', ')}`)
    if (!result.sent.length && !result.failed.length)
      toast.warning('No assignments to notify')
    await load()
  } catch (e) {
    toast.error(e instanceof Error ? e.message : 'Failed to send notifications')
  } finally {
    sending.value = false
  }
}

function formatDate(iso: string) {
  return new Date(iso + 'T00:00:00').toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
}

onMounted(load)
</script>

<template>
  <div v-if="!data" class="text-muted-foreground">Loading…</div>

  <div v-else class="space-y-8">
    <!-- Header row -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold tracking-tight">Today</h1>
        <p class="text-sm text-muted-foreground">
          {{ formatDate(data.schedule[0]?.date ?? '') }}
          <span v-if="data.notify_times.length" class="ml-2">
            · Notifications at {{ data.notify_times.join(', ') }}
          </span>
        </p>
      </div>
      <Button :disabled="sending" @click="sendNotifications">
        {{ sending ? 'Sending…' : 'Send Notifications' }}
      </Button>
    </div>

    <!-- Today's assignment cards -->
    <div v-if="data.schedule.length" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <Card
        v-for="(room, person) in data.schedule[0].assignments"
        :key="person"
      >
        <CardHeader class="pb-2">
          <CardTitle class="text-base">{{ person }}</CardTitle>
          <CardDescription>{{ room }}</CardDescription>
        </CardHeader>
        <CardContent>
          <div v-if="data.done_map[person]" class="flex items-center gap-2">
            <Badge variant="secondary">
              {{ data.done_map[person].done }}/{{ data.done_map[person].total }} done
            </Badge>
          </div>
          <p v-else class="text-sm text-muted-foreground">No tasks</p>
        </CardContent>
      </Card>
    </div>
    <p v-else class="text-sm text-muted-foreground">
      No rooms or members set up yet.
    </p>

    <!-- 14-day schedule -->
    <div v-if="data.schedule.length">
      <h2 class="mb-3 text-lg font-semibold">14-Day Schedule</h2>
      <div class="rounded-xl border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead
                v-for="person in Object.keys(data.schedule[0].assignments)"
                :key="person"
              >
                {{ person }}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="(day, i) in data.schedule"
              :key="day.date"
              :class="i === 0 ? 'font-medium' : ''"
            >
              <TableCell>{{ formatDate(day.date) }}</TableCell>
              <TableCell
                v-for="person in Object.keys(data.schedule[0].assignments)"
                :key="person"
              >
                {{ day.assignments[person] ?? '—' }}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
    </div>
  </div>
</template>
