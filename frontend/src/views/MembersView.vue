<script setup lang="ts">
import { ExternalLinkIcon, PlusIcon } from '@lucide/vue'
import { onMounted, ref } from 'vue'
import { toast } from 'vue-sonner'
import PageHeader from '@/components/PageHeader.vue'
import UserAvatar from '@/components/dashboard/UserAvatar.vue'
import ConfirmDialog from '@/components/states/ConfirmDialog.vue'
import EmptyState from '@/components/states/EmptyState.vue'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { api, ApiError } from '@/lib/api'
import type { Member } from '@/types'

const members = ref<Member[]>([])
const ntfyBase = ref('')
const loading = ref(true)
const newName = ref('')
const adding = ref(false)

async function load() {
  try {
    const data = await api.members()
    members.value = data.members
    ntfyBase.value = data.ntfy_base_url
  } catch {
    toast.error('Failed to load members')
  } finally {
    loading.value = false
  }
}

async function addMember() {
  const name = newName.value.trim()
  if (!name) return
  adding.value = true
  try {
    const member = await api.addMember(name)
    members.value.push(member)
    newName.value = ''
    toast.success(`Added '${name}'`)
  } catch (e) {
    toast.error(e instanceof ApiError ? e.message : 'Failed to add member')
  } finally {
    adding.value = false
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
    <PageHeader
      title="Members"
      :description="ntfyBase ? `Notifications go out via ${ntfyBase}` : 'Who shares the chores.'"
    />

    <form class="flex gap-2" @submit.prevent="addMember">
      <Input v-model="newName" placeholder="Name" class="max-w-xs" />
      <Button type="submit" :disabled="adding || !newName.trim()">
        <PlusIcon />
        Add member
      </Button>
    </form>

    <div v-if="loading" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <Skeleton v-for="i in 3" :key="i" class="h-32" />
    </div>

    <EmptyState
      v-else-if="!members.length"
      title="No members yet"
      description="Add whoever shares the chores — each gets a notification topic."
    />

    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <Card
        v-for="(member, i) in members"
        :key="member.name"
        class="rise-in gap-3 py-5"
        :style="{ animationDelay: `${Math.min(i, 8) * 40}ms` }"
      >
        <CardHeader class="pb-0">
          <div class="flex items-center gap-3">
            <UserAvatar :name="member.name" size="lg" />
            <CardTitle class="min-w-0 flex-1 truncate text-base">{{ member.name }}</CardTitle>
            <ConfirmDialog
              destructive
              :title="`Remove ${member.name}?`"
              description="They drop out of the rotation immediately."
              confirm-label="Remove"
              @confirm="deleteMember(member.name)"
            >
              <Button variant="ghost" size="xs" class="text-destructive">Remove</Button>
            </ConfirmDialog>
          </div>
        </CardHeader>
        <CardContent>
          <a
            :href="member.ntfy_url"
            target="_blank"
            rel="noopener"
            class="inline-flex items-center gap-1 font-mono text-xs text-muted-foreground transition-colors hover:text-primary"
          >
            {{ member.topic }}
            <ExternalLinkIcon class="size-3" />
          </a>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
