<script setup lang="ts">
import { Badge } from '@fisherrjd/ui/badge'
import { Button } from '@fisherrjd/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@fisherrjd/ui/card'
import { Checkbox } from '@fisherrjd/ui/checkbox'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogTitle } from '@fisherrjd/ui/dialog'
import { Input } from '@fisherrjd/ui/input'
import { PageHeader } from '@fisherrjd/ui/layout'
import { Separator } from '@fisherrjd/ui/separator'
import { Skeleton } from '@fisherrjd/ui/skeleton'
import { ConfirmDialog, EmptyState } from '@fisherrjd/ui/states'
import { swatch } from '@fisherrjd/ui/theme'
import { CameraIcon, PlusIcon, XIcon } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'
import { toast } from 'vue-sonner'
import { api, ApiError } from '@/lib/api'
import { uploadPhoto } from '@/lib/photo'
import type { ShoppingList } from '@/types'

// household shopping lists: one per store or purpose, shared and kept until
// someone removes them (unlike the daily checklists)
const lists = ref<ShoppingList[]>([])
const loading = ref(true)
const newList = ref('')
const adding = ref(false)
const newItemFor = ref<Record<string, string>>({})

const message = (e: unknown, fallback: string) => (e instanceof ApiError ? e.message : fallback)

// every mutation answers with the list's new state; swap it in place
function replace(updated: ShoppingList) {
  const i = lists.value.findIndex((l) => l.name === updated.name)
  if (i >= 0) lists.value[i] = updated
}

async function load() {
  try {
    lists.value = await api.lists()
  } catch {
    toast.error('Failed to load lists')
  } finally {
    loading.value = false
  }
}

async function addList() {
  const name = newList.value.trim()
  if (!name) return
  adding.value = true
  try {
    lists.value.push(await api.addList(name))
    newList.value = ''
    toast.success(`Added list '${name}'`)
  } catch (e) {
    toast.error(message(e, 'Failed to add list'))
  } finally {
    adding.value = false
  }
}

async function deleteList(name: string) {
  try {
    await api.deleteList(name)
    lists.value = lists.value.filter((l) => l.name !== name)
    toast.success(`Removed list '${name}'`)
  } catch (e) {
    toast.error(message(e, 'Failed to remove list'))
  }
}

// photo picked in the add form, kept per list (with an object URL for the chip preview)
const attached = ref<Record<string, { file: File; url: string }>>({})
const attachInput = ref<HTMLInputElement | null>(null)
const attachTarget = ref('')

function pickAttach(list: string) {
  attachTarget.value = list
  attachInput.value?.click()
}

function onAttachPicked(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !attachTarget.value) return
  clearAttached(attachTarget.value)
  attached.value[attachTarget.value] = { file, url: URL.createObjectURL(file) }
}

function clearAttached(list: string) {
  const a = attached.value[list]
  if (!a) return
  URL.revokeObjectURL(a.url)
  delete attached.value[list]
}

async function addItem(list: string) {
  const item = (newItemFor.value[list] ?? '').trim()
  if (!item) return
  const photo = attached.value[list]?.file
  try {
    replace(await api.addListItem(list, item))
    newItemFor.value[list] = ''
  } catch (e) {
    toast.error(message(e, 'Failed to add item'))
    return
  }
  if (!photo) return
  try {
    replace(await uploadPhoto(list, item, photo))
  } catch (e) {
    toast.error(message(e, 'Failed to save photo'))
  }
  clearAttached(list)
}

async function setItem(list: string, item: string, done: boolean) {
  try {
    replace(await api.setListItem(list, item, done))
  } catch (e) {
    toast.error(message(e, 'Failed to update item'))
  }
}

async function deleteItem(list: string, item: string) {
  try {
    replace(await api.deleteListItem(list, item))
  } catch (e) {
    toast.error(message(e, 'Failed to remove item'))
  }
}

async function clearBought(list: string) {
  try {
    const { removed, ...updated } = await api.clearBought(list)
    replace(updated)
    toast.success(`Cleared ${removed} bought item${removed === 1 ? '' : 's'} from ${list}`)
  } catch (e) {
    toast.error(message(e, 'Failed to clear bought items'))
  }
}

// photos: one hidden picker shared by the row buttons and the viewer's Replace.
// No `capture` attribute, so phones offer camera or gallery.
const fileInput = ref<HTMLInputElement | null>(null)
const pickTarget = ref<{ list: string; item: string; replacing: boolean } | null>(null)
const viewing = ref<{ list: string; item: string } | null>(null)

const viewedItem = computed(
  () => lists.value.find((l) => l.name === viewing.value?.list)?.items.find((i) => i.name === viewing.value?.item) ?? null,
)
const viewerOpen = computed({
  get: () => viewedItem.value !== null,
  set: (v) => {
    if (!v) viewing.value = null
  },
})

function pickPhoto(list: string, item: string, replacing: boolean) {
  pickTarget.value = { list, item, replacing }
  fileInput.value?.click()
}

async function onPicked(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  const target = pickTarget.value
  input.value = ''
  if (!file || !target) return
  try {
    replace(await uploadPhoto(target.list, target.item, file))
    toast.success(target.replacing ? `Photo replaced on ${target.item}` : `Photo added to ${target.item}`)
  } catch (err) {
    toast.error(message(err, 'Failed to save photo'))
  }
}

async function removePhoto(list: string, item: string) {
  try {
    replace(await api.removeListPhoto(list, item))
    viewing.value = null
    toast.success(`Photo removed from ${item}`)
  } catch (e) {
    toast.error(message(e, 'Failed to save photo'))
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <PageHeader
      title="Lists"
      description="One list per store or purpose. Shared with the whole household and kept until you remove it."
    />

    <form class="flex gap-2" @submit.prevent="addList">
      <Input v-model="newList" placeholder="List name (e.g. Costco, Kroger, Target)" class="max-w-xs" />
      <Button type="submit" :disabled="adding || !newList.trim()">
        <PlusIcon />
        Add list
      </Button>
    </form>

    <div v-if="loading" class="grid gap-4 sm:grid-cols-2">
      <Skeleton v-for="i in 2" :key="i" class="h-48" />
    </div>

    <EmptyState v-else-if="!lists.length" title="No lists yet" description="Add one above." />

    <div v-else class="grid items-start gap-4 sm:grid-cols-2">
      <!-- each list gets its own color: the header band, and (via --primary) its checkboxes -->
      <Card
        v-for="(list, i) in lists"
        :key="list.name"
        class="rise-in gap-0 overflow-hidden p-0"
        :style="[{ animationDelay: `${Math.min(i, 8) * 40}ms` }, swatch(i, { primary: true })]"
      >
        <CardHeader class="bg-swatch px-5 py-3 text-swatch-foreground">
          <div class="flex items-center justify-between gap-2">
            <CardTitle class="flex items-center gap-2 text-lg">
              {{ list.name }}
              <Badge v-if="list.items.length" variant="outline" class="border-current bg-background/25 text-swatch-foreground">
                {{ list.remaining ? `${list.remaining} to buy` : 'all bought' }}
              </Badge>
            </CardTitle>
            <ConfirmDialog
              destructive
              :title="`Remove the ${list.name} list?`"
              description="Everything on it goes too."
              confirm-label="Remove list"
              @confirm="deleteList(list.name)"
            >
              <Button variant="ghost" size="xs" class="text-swatch-foreground hover:bg-background/25">Remove</Button>
            </ConfirmDialog>
          </div>
        </CardHeader>
        <CardContent class="space-y-3 px-5 py-4">
          <div v-if="list.items.length" class="space-y-1">
            <div
              v-for="item in list.items"
              :key="item.name"
              class="group -mx-2 flex items-center gap-3 rounded-md px-2 py-1 transition-colors hover:bg-muted/50"
            >
              <Checkbox
                :id="`${list.name}-${item.name}`"
                :model-value="item.done"
                @update:model-value="(v) => setItem(list.name, item.name, v === true)"
              />
              <label
                :for="`${list.name}-${item.name}`"
                class="flex-1 cursor-pointer text-sm"
                :class="item.done ? 'text-muted-foreground line-through' : ''"
              >
                {{ item.name }}
              </label>
              <button
                v-if="item.image_url"
                type="button"
                class="size-10 shrink-0 overflow-hidden rounded-md border"
                :aria-label="`View photo of ${item.name}`"
                @click="viewing = { list: list.name, item: item.name }"
              >
                <img :src="item.image_url" :alt="item.name" class="size-full object-cover" />
              </button>
              <button
                v-else
                type="button"
                class="flex size-10 shrink-0 items-center justify-center rounded-md border border-dashed text-muted-foreground transition-colors hover:text-foreground"
                :aria-label="`Add photo to ${item.name}`"
                @click="pickPhoto(list.name, item.name, false)"
              >
                <CameraIcon class="size-4" />
              </button>
              <button
                type="button"
                class="text-muted-foreground/50 transition-colors hover:text-destructive"
                :aria-label="`Remove ${item.name}`"
                @click="deleteItem(list.name, item.name)"
              >
                <XIcon class="size-3.5" />
              </button>
            </div>
          </div>
          <p v-else class="text-xs text-muted-foreground">Nothing on the list.</p>

          <Button v-if="list.bought" variant="outline" size="sm" @click="clearBought(list.name)">
            Clear {{ list.bought }} bought
          </Button>

          <Separator />

          <form class="flex gap-2" @submit.prevent="addItem(list.name)">
            <Input v-model="newItemFor[list.name]" placeholder="Add an item…" class="h-8 text-sm" />
            <Button
              type="button"
              size="sm"
              variant="outline"
              aria-label="Attach a photo"
              @click="pickAttach(list.name)"
            >
              <CameraIcon />
            </Button>
            <Button type="submit" size="sm" variant="secondary" :disabled="!newItemFor[list.name]?.trim()">
              Add
            </Button>
          </form>
          <div v-if="attached[list.name]" class="flex items-center gap-2 text-xs text-muted-foreground">
            <img :src="attached[list.name].url" alt="" class="size-8 rounded-md border object-cover" />
            <span class="flex-1">Photo attached</span>
            <button
              type="button"
              class="transition-colors hover:text-destructive"
              aria-label="Remove attached photo"
              @click="clearAttached(list.name)"
            >
              <XIcon class="size-3.5" />
            </button>
          </div>
        </CardContent>
      </Card>
    </div>

    <input ref="fileInput" type="file" accept="image/*" class="hidden" @change="onPicked" />
    <input ref="attachInput" type="file" accept="image/*" class="hidden" @change="onAttachPicked" />

    <Dialog v-model:open="viewerOpen">
      <DialogContent v-if="viewedItem && viewing">
        <DialogTitle>{{ viewedItem.name }}</DialogTitle>
        <DialogDescription>On {{ viewing.list }}</DialogDescription>
        <img
          v-if="viewedItem.image_url"
          :src="viewedItem.image_url"
          :alt="viewedItem.name"
          class="max-h-[60vh] w-full object-contain"
        />
        <DialogFooter>
          <Button type="button" variant="outline" @click="pickPhoto(viewing.list, viewing.item, true)">
            Replace photo
          </Button>
          <Button type="button" variant="destructive" @click="removePhoto(viewing.list, viewing.item)">
            Remove photo
          </Button>
          <Button type="button" variant="secondary" @click="viewing = null">Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
