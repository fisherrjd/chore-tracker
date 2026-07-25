import { ref, watchEffect } from 'vue'
import { THEMES, type ThemeId } from '@/lib/themes'

const THEME_KEY = 'app.theme'
const MODE_KEY = 'app.mode'

type Mode = 'light' | 'dark'

function initialTheme(): ThemeId {
  const saved = localStorage.getItem(THEME_KEY)
  return THEMES.some((t) => t.id === saved) ? (saved as ThemeId) : THEMES[0].id
}

function initialMode(): Mode {
  const saved = localStorage.getItem(MODE_KEY)
  if (saved === 'light' || saved === 'dark') return saved
  return 'dark' // dark over light, always
}

// module-scope singleton: every component shares the same theme state
const theme = ref<ThemeId>(initialTheme())
const mode = ref<Mode>(initialMode())

watchEffect(() => {
  document.documentElement.dataset.theme = theme.value
  localStorage.setItem(THEME_KEY, theme.value)
})

watchEffect(() => {
  document.documentElement.classList.toggle('dark', mode.value === 'dark')
  localStorage.setItem(MODE_KEY, mode.value)
})

export function useTheme() {
  const setTheme = (id: ThemeId) => {
    theme.value = id
  }
  const toggleMode = () => {
    mode.value = mode.value === 'dark' ? 'light' : 'dark'
  }
  return { theme, mode, setTheme, toggleMode }
}
