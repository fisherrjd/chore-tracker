<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { toast } from 'vue-sonner'
import { api, ApiError } from '@/lib/api'
import type { Member } from '@/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'

const members = ref<Member[]>([])
const ntfyBase = ref('')
const newName = ref('')
const loading = ref(false)

async function load() {
  try {
    const data = await api.members()
    members.value = data.members
    ntfyBase.value = data.ntfy_base_url
  } catch {
    toast.error('Failed to load members')
  }
}

async function addMember() {
  const name = newName.value.trim()
  if (!name) return
  loading.value = true
  try {
    const member = await api.addMember(name)
    members.value.push(member)
    newName.value = ''
    toast.success(`Added '${name}'`)
  } catch (e) {
    toast.error(e instanceof ApiError ? e.message : 'Failed to add member')
  } finally {
    loading.value = false
  }
}

async function deleteMember(name: string) {
  try {
    await api.deleteMember(name)
    members.value = members.value.filter((m) => m.name !== name)
    toast.success(`Removed '${name}'`)
  } catch (e) {
    toast.error(e instanceof ApiError ? e.message : 'Failed to remove member')
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold tracking-tight">Members</h1>

    <!-- Add member -->
    <div class="flex gap-2">
      <Input
        v-model="newName"
        placeholder="Name"
        class="max-w-xs"
        @keydown.enter="addMember"
      />
      <Button :disabled="loading || !newName.trim()" @click="addMember">Add Member</Button>
    </div>

    <p v-if="!members.length" class="text-sm text-muted-foreground">No members yet.</p>

    <!-- Member cards -->
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <Card v-for="member in members" :key="member.name">
        <CardHeader class="pb-2">
          <div class="flex items-center justify-between">
            <CardTitle class="text-base">{{ member.name }}</CardTitle>
            <Button variant="destructive" size="sm" @click="deleteMember(member.name)">
              Remove
            </Button>
          </div>
          <CardDescription>
            ntfy topic:
            <a
              :href="member.ntfy_url"
              target="_blank"
              rel="noopener"
              class="font-mono text-xs underline hover:no-underline"
            >{{ member.topic }}</a>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p class="break-all font-mono text-xs text-muted-foreground">
            {{ member.ntfy_url }}
          </p>
        </CardContent>
      </Card>
    </div>

    <p v-if="ntfyBase" class="text-xs text-muted-foreground">
      Notification base URL: <span class="font-mono">{{ ntfyBase }}</span>
    </p>
  </div>
</template>
