import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// crypto.randomUUID only exists in secure contexts — plain-http access
// (e.g. over the tailnet) needs the getRandomValues fallback.
export function uid(): string {
  return (
    crypto.randomUUID?.() ??
    Array.from(crypto.getRandomValues(new Uint8Array(8)), (b) =>
      b.toString(16).padStart(2, '0'),
    ).join('')
  )
}
