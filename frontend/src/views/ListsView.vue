<script setup lang="ts">
import { Badge } from '@fisherrjd/ui/badge'
import { Button } from '@fisherrjd/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@fisherrjd/ui/card'
import { Checkbox } from '@fisherrjd/ui/checkbox'
import { Input } from '@fisherrjd/ui/input'
import { PageHeader } from '@fisherrjd/ui/layout'
import { Separator } from '@fisherrjd/ui/separator'
import { Skeleton } from '@fisherrjd/ui/skeleton'
import { ConfirmDialog, EmptyState } from '@fisherrjd/ui/states'
import { swatch } from '@fisherrjd/ui/theme'
import { PlusIcon, XIcon } from '@lucide/vue'
import { onMounted, ref } from 'vue'
import { toast } from 'vue-sonner'
import { api, ApiError } from '@/lib/api'
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

async function addItem(list: string) {
  const item = (newItemFor.value[list] ?? '').trim()
  if (!item) return
  try {
    replace(await api.addListItem(list, item))
    newItemFor.value[list] = ''
  } catch (e) {
    toast.error(message(e, 'Failed to add item'))
  }
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
            <Button type="submit" size="sm" variant="secondary" :disabled="!newItemFor[list.name]?.trim()">
              Add
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  </div>
</template>
