<script setup lang="ts">
import { PlusIcon, XIcon } from '@lucide/vue'
import { onMounted, ref } from 'vue'
import { toast } from 'vue-sonner'
import PageHeader from '@/components/PageHeader.vue'
import ConfirmDialog from '@/components/states/ConfirmDialog.vue'
import EmptyState from '@/components/states/EmptyState.vue'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { api, ApiError } from '@/lib/api'
import type { Room } from '@/types'

const rooms = ref<Room[]>([])
const loading = ref(true)
const newRoom = ref('')
const adding = ref(false)
const newTaskFor = ref<Record<string, string>>({})

async function load() {
  try {
    rooms.value = await api.rooms()
  } catch {
    toast.error('Failed to load rooms')
  } finally {
    loading.value = false
  }
}

async function addRoom() {
  const name = newRoom.value.trim()
  if (!name) return
  adding.value = true
  try {
    const room = await api.addRoom(name)
    rooms.value.push(room)
    newRoom.value = ''
    toast.success(`Added room '${name}'`)
  } catch (e) {
    toast.error(e instanceof ApiError ? e.message : 'Failed to add room')
  } finally {
    adding.value = false
  }
}

async function deleteRoom(name: string) {
  try {
    await api.deleteRoom(name)
    rooms.value = rooms.value.filter((r) => r.name !== name)
    toast.success(`Removed room '${name}'`)
  } catch (e) {
    toast.error(e instanceof ApiError ? e.message : 'Failed to remove room')
  }
}

async function addTask(roomName: string) {
  const task = (newTaskFor.value[roomName] ?? '').trim()
  if (!task) return
  try {
    await api.addTask(roomName, task)
    const room = rooms.value.find((r) => r.name === roomName)
    if (room) room.tasks.push(task)
    newTaskFor.value[roomName] = ''
  } catch (e) {
    toast.error(e instanceof ApiError ? e.message : 'Failed to add task')
  }
}

async function deleteTask(roomName: string, task: string) {
  try {
    await api.deleteTask(roomName, task)
    const room = rooms.value.find((r) => r.name === roomName)
    if (room) room.tasks = room.tasks.filter((t) => t !== task)
  } catch (e) {
    toast.error(e instanceof ApiError ? e.message : 'Failed to remove task')
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <PageHeader title="Rooms" description="Each room's task list becomes someone's checklist." />

    <form class="flex gap-2" @submit.prevent="addRoom">
      <Input v-model="newRoom" placeholder="New room name" class="max-w-xs" />
      <Button type="submit" :disabled="adding || !newRoom.trim()">
        <PlusIcon />
        Add room
      </Button>
    </form>

    <div v-if="loading" class="grid gap-4 sm:grid-cols-2">
      <Skeleton v-for="i in 2" :key="i" class="h-48" />
    </div>

    <EmptyState
      v-else-if="!rooms.length"
      title="No rooms yet"
      description="Add the first room above — tasks come next."
    />

    <div v-else class="grid gap-4 sm:grid-cols-2">
      <Card
        v-for="(room, i) in rooms"
        :key="room.name"
        class="rise-in gap-4 py-5"
        :style="{ animationDelay: `${Math.min(i, 8) * 40}ms` }"
      >
        <CardHeader class="pb-0">
          <div class="flex items-center justify-between gap-2">
            <CardTitle class="text-base">{{ room.name }}</CardTitle>
            <ConfirmDialog
              destructive
              :title="`Delete ${room.name}?`"
              description="Its tasks go with it, and the rotation reshuffles."
              confirm-label="Delete room"
              @confirm="deleteRoom(room.name)"
            >
              <Button variant="ghost" size="xs" class="text-destructive">Remove</Button>
            </ConfirmDialog>
          </div>
        </CardHeader>
        <CardContent class="space-y-3">
          <div v-if="room.tasks.length" class="space-y-1">
            <div
              v-for="task in room.tasks"
              :key="task"
              class="group -mx-2 flex items-center justify-between rounded-md px-2 py-1 text-sm transition-colors hover:bg-muted/50"
            >
              <span>{{ task }}</span>
              <button
                class="text-muted-foreground/50 transition-colors hover:text-destructive"
                :aria-label="`Remove ${task}`"
                @click="deleteTask(room.name, task)"
              >
                <XIcon class="size-3.5" />
              </button>
            </div>
          </div>
          <p v-else class="text-xs text-muted-foreground">No tasks yet.</p>

          <Separator />

          <form class="flex gap-2" @submit.prevent="addTask(room.name)">
            <Input v-model="newTaskFor[room.name]" placeholder="Add task" class="h-8 text-sm" />
            <Button
              type="submit"
              size="sm"
              variant="secondary"
              :disabled="!newTaskFor[room.name]?.trim()"
            >
              Add
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
