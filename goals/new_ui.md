# TODO: UI Refinement for Mobile-First AI Agent Interface

The overall objective is to transform the current user interface into a sleek, modern, highly responsive UI tailored specifically for mobile devices, with a strict focus on fitting perfectly on an iPhone (testing against standard iPhone 13/14/15/16 screen dimensions, 390x844px and up). 

The AI agent should feel native, snappy, and clear of desktop clutter.

---

## 🎯 Global System Prompt Instructions for UI Generation

When regenerating or adjusting components, ensure the following principles are strictly maintained:
- **Design System:** Use a minimalist, modern aesthetic. Prefer a clean dark/light ambient background over stark pure black or white. Use soft, desaturated accent colors (e.g., slate, deep indigo, or sage green) instead of neon colors.
- **Box Sizing:** Always use `box-sizing: border-box` to prevent elements with padding from overflowing the iPhone screen bounds.
- **Layout Model:** Use strict vertical stacking, block-level centering, or standard CSS tables where vertical alignment is needed. *Avoid flexbox/grid if compiling down to environments with limited layout engines (like PDF previewers), otherwise use responsive media queries targeting max-width: 480px.*
- **No Horizontal Scroll:** Zero horizontal overflow on the body element. All content must wrap naturally.

---

## 📋 High-Priority UI Checklist

### 1. Layout & Viewport Configuration
- [ ] **Viewport Meta Tag:** Verify or inject `<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">` to prevent unwanted auto-zooming on input focus on iOS.
- [ ] **Page Padding:** Establish clean, consistent margins around the viewport. Set `@page` or root body boundaries to a tight but clean `12mm` or `15px` margin.
- [ ] **Safe Area Insets:** Implement iOS safe-area-inset padding for iPhones with notches/dynamic islands (`padding-top: env(safe-area-inset-top);`, `padding-bottom: env(safe-area-inset-bottom);`).

### 2. Header & Branding
- [ ] **Mobile Banner:** Create a compact, sticky top header bar with a muted accent background (e.g., slate grey or deep navy). 
- [ ] **Minimalist Header Typography:** Change header text sizes to match mobile constraints. Scale down title fonts to `16pt` - `18pt` maximum.
- [ ] **Status Indicator:** Add a subtle, pulsating inline status dot showing the AI Agent's connectivity state (e.g., "● Online", utilizing a desaturated soft green).

### 3. Chat Interface & Stream Flow (The Core Experience)
- [ ] **Message Bubble Constraints:** Ensure message bubbles cap their width at `85%` of the screen width so they look like standard mobile chat bubbles.
- [ ] **Alternating Bubble Styles:**
  - **User Messages:** Crisp, light tint or subtle accent color background, right-aligned.
  - **AI Agent Responses:** Pure background or contrasting soft panel background, left-aligned.
- [ ] **Font Sizing:** Tighten body text inside bubbles to `10pt` or `11pt` for readability without causing text to blow up on smaller viewports.
- [ ] **Code Block Wrap:** Force code blocks (`<pre>`, `<code>`) to use `white-space: pre-wrap;` and `word-break: break-word;` so they do not break layout width on iPhone screens.

### 4. Input Controls & Interactivity
- [ ] **Sticky Bottom Input Bar:** Fix the chat input container to the absolute bottom of the viewport so it is always accessible via thumb.
- [ ] **Mobile-Friendly Form Fields:** Input elements must have a minimum font size of `16px` (or equivalent pt) to explicitly bypass iOS Safari's default zoom-on-focus behavior.
- [ ] **Compact Button Targets:** Style buttons to be easily tappable (minimum `44x44px` hit area per Apple Human Interface Guidelines) but visually sleek with rounded corners (`border-radius: 8px`).

### 5. Visual Refinements & Polish
- [ ] **Accent Sidebar Elimination:** Remove full-width or heavy vertical accent lines (like thick left borders on cards) that look blocky on phone screens. Instead, use a subtle bottom border or soft background paneling.
- [ ] **Scroll Snapping:** Ensure the message area automatically scrolls to the absolute bottom when new text tokens stream in from the AI.
- [ ] **Typography Cleanup:** Ensure no equations or mathematical fallback blocks render as raw unstyled monospace text. Wrap variables or mathematical steps cleanly in styled inline spans (`font-family: 'Times New Roman', serif; font-style: italic;`).
