import { api, ApiError } from '@/lib/api'
import type { ShoppingList } from '@/types'

export const TARGET_BYTES = 900 * 1024
export const MAX_SIDE = 1280
export const MAX_PHOTO_BYTES = 10 * 1024 * 1024

function toJpeg(canvas: HTMLCanvasElement, quality: number): Promise<Blob | null> {
  return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality))
}

/** Downscale/re-encode a big photo; small ones come back untouched. */
export async function shrinkPhoto(file: File): Promise<File | Blob> {
  try {
    const bitmap = await createImageBitmap(file)
    const longest = Math.max(bitmap.width, bitmap.height)
    if (file.size <= TARGET_BYTES && longest <= MAX_SIDE) {
      bitmap.close?.()
      return file
    }
    const scale = Math.min(1, MAX_SIDE / longest)
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(bitmap.width * scale))
    canvas.height = Math.max(1, Math.round(bitmap.height * scale))
    const ctx = canvas.getContext('2d')
    if (!ctx) return file
    ctx.fillStyle = '#fff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    bitmap.close?.()
    let blob: Blob | null = null
    for (const q of [0.8, 0.6, 0.45]) {
      blob = await toJpeg(canvas, q)
      if (!blob) return file
      if (blob.size <= TARGET_BYTES) break
    }
    return blob ?? file
  } catch {
    return file
  }
}

export async function uploadPhoto(list: string, item: string, file: File): Promise<ShoppingList> {
  const blob = await shrinkPhoto(file)
  if (blob.size > MAX_PHOTO_BYTES) throw new ApiError(413, 'Photo is too big (max 10 MB)')
  return api.setListPhoto(list, item, blob, blob === file ? file.name : 'photo.jpg')
}
