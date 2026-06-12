<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { toast } from 'vue-sonner'
import { api, ApiError } from '@/lib/api'
import type { Room } from '@/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'

const rooms = ref<Room[]>([])
const newRoom = ref('')
const newTaskFor = ref<Record<string, string>>({})
const loading = ref(false)

async function load() {
  try {
    rooms.value = await api.rooms()
  } catch {
    toast.error('Failed to load rooms')
  }
}

async function addRoom() {
  const name = newRoom.value.trim()
  if (!name) return
  loading.value = true
  try {
    const room = await api.addRoom(name)
    rooms.value.push(room)
    newRoom.value = ''
    toast.success(`Added room '${name}'`)
  } catch (e) {
    toast.error(e instanceof ApiError ? e.message : 'Failed to add room')
  } finally {
    loading.value = false
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
    toast.success(`Added task to ${roomName}`)
  } catch (e) {
    toast.error(e instanceof ApiError ? e.message : 'Failed to add task')
  }
}

async function deleteTask(roomName: string, task: string) {
  try {
    await api.deleteTask(roomName, task)
    const room = rooms.value.find((r) => r.name === roomName)
    if (room) room.tasks = room.tasks.filter((t) => t !== task)
    toast.success(`Removed task from ${roomName}`)
  } catch (e) {
    toast.error(e instanceof ApiError ? e.message : 'Failed to remove task')
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold tracking-tight text-primary">Rooms</h1>

    <!-- Add room -->
    <div class="flex gap-2">
      <Input
        v-model="newRoom"
        placeholder="New room name"
        class="max-w-xs"
        @keydown.enter="addRoom"
      />
      <Button :disabled="loading || !newRoom.trim()" @click="addRoom">Add Room</Button>
    </div>

    <p v-if="!rooms.length" class="text-sm text-muted-foreground">No rooms yet.</p>

    <!-- Room cards -->
    <div class="grid gap-4 sm:grid-cols-2">
      <Card v-for="room in rooms" :key="room.name">
        <CardHeader class="pb-3">
          <div class="flex items-center justify-between">
            <CardTitle class="text-base">{{ room.name }}</CardTitle>
            <Button variant="destructive" size="sm" @click="deleteRoom(room.name)">
              Remove
            </Button>
          </div>
        </CardHeader>
        <CardContent class="space-y-3">
          <!-- Task list -->
          <div v-if="room.tasks.length" class="space-y-1">
            <div
              v-for="task in room.tasks"
              :key="task"
              class="flex items-center justify-between rounded-md px-2 py-1 text-sm hover:bg-muted/50"
            >
              <span>{{ task }}</span>
              <button
                class="text-xs text-muted-foreground hover:text-destructive"
                @click="deleteTask(room.name, task)"
              >
                ×
              </button>
            </div>
          </div>
          <p v-else class="text-xs text-muted-foreground">No tasks</p>

          <Separator />

          <!-- Add task -->
          <div class="flex gap-2">
            <Input
              v-model="newTaskFor[room.name]"
              placeholder="Add task"
              class="h-8 text-xs"
              @keydown.enter="addTask(room.name)"
            />
            <Button
              size="sm"
              variant="secondary"
              :disabled="!newTaskFor[room.name]?.trim()"
              @click="addTask(room.name)"
            >
              Add
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
