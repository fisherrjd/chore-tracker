<script setup lang="ts">
import { ArrowLeftIcon } from '@lucide/vue'
import { useDebounceFn } from '@vueuse/core'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { toast } from 'vue-sonner'
import PageHeader from '@/components/PageHeader.vue'
import Checklist from '@/components/project/Checklist.vue'
import SaveIndicator from '@/components/project/SaveIndicator.vue'
import ErrorState from '@/components/states/ErrorState.vue'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { api, ApiError } from '@/lib/api'
import type { ChecklistData } from '@/types'

const route = useRoute()
const member = route.params.member as string

const data = ref<ChecklistData | null>(null)
const done = ref<string[]>([])
const notFound = ref(false)
const saveState = ref<'saved' | 'saving' | 'error'>('saved')

// suppress the save watcher while load() seeds `done`
let seeding = false

async function load() {
  try {
    const result = await api.checklist(member)
    data.value = result
    seeding = true
    done.value = result.done
    await nextTick()
    seeding = false
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound.value = true
    else toast.error('Failed to load checklist')
  }
}

const save = useDebounceFn(async () => {
  try {
    await api.updateChecklist(member, done.value)
    saveState.value = 'saved'
  } catch {
    saveState.value = 'error'
  }
}, 400)

watch(done, () => {
  if (seeding || !data.value) return
  saveState.value = 'saving'
  void save()
})

const items = computed(() => (data.value?.tasks ?? []).map((t) => ({ id: t, label: t })))

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
        :description="`Today's room: ${data.room_name ?? 'none assigned'}`"
      >
        <template #actions>
          <SaveIndicator :state="saveState" />
        </template>
      </PageHeader>

      <Card class="p-5">
        <Checklist v-if="items.length" v-model:done="done" :items="items" />
        <p v-else class="text-sm text-muted-foreground">No tasks for this room.</p>
      </Card>
    </template>
  </div>
</template>
