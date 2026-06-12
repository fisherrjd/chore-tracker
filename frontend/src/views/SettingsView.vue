<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { toast } from 'vue-sonner'
import { api, ApiError } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'

const notifyTimes = ref<string[]>([])
const timezone = ref('')
const newTime = ref('')
const loading = ref(false)

async function load() {
  try {
    const data = await api.settings()
    notifyTimes.value = data.notify_times
    timezone.value = data.timezone
  } catch {
    toast.error('Failed to load settings')
  }
}

async function addTime() {
  const time = newTime.value.trim()
  if (!time) return
  loading.value = true
  try {
    const data = await api.addNotifyTime(time)
    notifyTimes.value = data.notify_times
    newTime.value = ''
    toast.success(`Added notification at ${time}`)
  } catch (e) {
    toast.error(e instanceof ApiError ? e.message : 'Failed to add time')
  } finally {
    loading.value = false
  }
}

async function deleteTime(time: string) {
  try {
    const data = await api.deleteNotifyTime(time)
    notifyTimes.value = data.notify_times
    toast.success(`Removed notification at ${time}`)
  } catch (e) {
    toast.error(e instanceof ApiError ? e.message : 'Failed to remove time')
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold tracking-tight text-primary">Settings</h1>

    <Card class="max-w-md">
      <CardHeader>
        <CardTitle>Notification Times</CardTitle>
        <CardDescription>
          Daily notifications fire at these times in {{ timezone }}.
        </CardDescription>
      </CardHeader>
      <CardContent class="space-y-4">
        <!-- Existing times -->
        <div v-if="notifyTimes.length" class="flex flex-wrap gap-2">
          <div
            v-for="t in notifyTimes"
            :key="t"
            class="flex items-center gap-1"
          >
            <Badge variant="secondary" class="font-mono">{{ t }}</Badge>
            <button
              class="rounded-sm text-muted-foreground hover:text-destructive"
              @click="deleteTime(t)"
            >
              ×
            </button>
          </div>
        </div>
        <p v-else class="text-sm text-muted-foreground">No notification times set.</p>

        <!-- Add time -->
        <div class="flex gap-2">
          <Input
            v-model="newTime"
            type="time"
            placeholder="HH:MM"
            class="w-32"
            @keydown.enter="addTime"
          />
          <Button :disabled="loading || !newTime.trim()" @click="addTime">Add</Button>
        </div>
      </CardContent>
    </Card>

    <Card class="max-w-md">
      <CardHeader>
        <CardTitle>Timezone</CardTitle>
        <CardDescription>
          "Today" is determined by this timezone.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <p class="font-mono text-sm">{{ timezone || '—' }}</p>
        <p class="mt-1 text-xs text-muted-foreground">
          Edit <code>config.yaml</code> to change the timezone.
        </p>
      </CardContent>
    </Card>
  </div>
</template>
