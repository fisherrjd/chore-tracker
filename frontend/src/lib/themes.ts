// the theme registry: pickers and the styleguide swatches are driven by this.
// adding a preset = new file in assets/themes/ + @import in assets/index.css
// + one entry here (+ the pre-paint list in index.html).
export const THEMES = [
  { id: 'evergreen', label: 'Evergreen' },
  { id: 'dusk', label: 'Dusk' },
  { id: 'earthy', label: 'Earthy' },
  { id: 'grapebox', label: 'Grapebox' },
] as const

export type ThemeId = (typeof THEMES)[number]['id']

// every token a preset must define, in display order
export const THEME_TOKENS = [
  'background',
  'foreground',
  'card',
  'card-foreground',
  'popover',
  'popover-foreground',
  'primary',
  'primary-foreground',
  'secondary',
  'secondary-foreground',
  'muted',
  'muted-foreground',
  'accent',
  'accent-foreground',
  'destructive',
  'destructive-foreground',
  'border',
  'input',
  'ring',
] as const
