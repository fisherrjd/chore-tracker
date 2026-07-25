<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { toast } from 'vue-sonner'
import PageHeader from '@/components/PageHeader.vue'
import FormField from '@/components/forms/FormField.vue'
import SettingsSection from '@/components/forms/SettingsSection.vue'
import TagInput from '@/components/forms/TagInput.vue'
import { api, ApiError } from '@/lib/api'

const times = ref<string[]>([])
const timezone = ref('')

// the API mutates one time per call, TagInput edits the whole array —
// diff against the server's copy and replay the changes.
let server: string[] = []

async function load() {
  try {
    const data = await api.settings()
    server = data.notify_times
    times.value = [...server]
    timezone.value = data.timezone
  } catch {
    toast.error('Failed to load settings')
  }
}

watch(times, async (next) => {
  const added = next.filter((t) => !server.includes(t))
  const removed = server.filter((t) => !next.includes(t))
  if (!added.length && !removed.length) return
  try {
    let latest = server
    for (const t of added) latest = (await api.addNotifyTime(t)).notify_times
    for (const t of removed) latest = (await api.deleteNotifyTime(t)).notify_times
    server = latest
    // the backend may normalize/sort — mirror its truth if it differs
    if (JSON.stringify(latest) !== JSON.stringify(next)) times.value = [...latest]
  } catch (e) {
    toast.error(e instanceof ApiError ? e.message : 'Failed to update times')
    times.value = [...server]
  }
})

onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-2xl space-y-6">
    <PageHeader title="Settings" description="Notification schedule and timezone." />

    <SettingsSection
      title="Notification times"
      :description="`Daily notifications fire at these times${timezone ? ` in ${timezone}` : ''}.`"
    >
      <FormField
        v-slot="{ id }"
        label="Times"
        hint="Changes save immediately — no button to forget."
      >
        <TagInput :id="id" v-model="times" type="time" mono />
      </FormField>
    </SettingsSection>

    <SettingsSection title="Timezone" description="&quot;Today&quot; is decided in this timezone.">
      <p class="font-mono text-sm">{{ timezone || '—' }}</p>
      <p class="text-xs text-muted-foreground">
        Edit <code class="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">config.yaml</code> to
        change it.
      </p>
    </SettingsSection>
  </div>
</template>
