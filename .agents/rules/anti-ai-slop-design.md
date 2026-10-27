# Anti-AI-Slop UI/UX Design Rules & Responsive Guidelines

You are strictly prohibited from generating generic, template-heavy, or "AI-slop" user interfaces. All web interfaces in this project must look human-designed, handcrafted, purposeful, and professional across all devices (Mobile, Tablet, Desktop).

---

## 1. Core Anti-AI-Slop Prohibitions (Zero Tolerance)

1. **NO "Card Inside Card" (Double Cards / Nested Boxes):**
   - Never nest containers with their own borders, backgrounds, and drop shadows inside another card. Keep layouts flat, unified, and demarcated with subtle divider lines or clean whitespace, not layers of dark boxes.
2. **NO Generic Gradient Clichés:**
   - Never use the generic AI purple-to-blue or cyan-to-purple gradient soup.
   - Use curated, purposeful, low-saturation backgrounds with intentional semantic accents (e.g., Institutional Emerald `#10b981` for gains, Crimson `#ef4444` for risk/loss, Slate `#0f172a` for structure).
3. **NO Decorative Status Emojis as Interface Icons:**
   - Use clean, vector SVG icons or crisp typographic indicators. Never use raw consumer emojis (🚀, 🔥, 💎, 🤑) in professional financial or trading interfaces.
4. **NO Eyebrow Taglines or Arbitrary Word Highlights:**
   - Do not slap arbitrary uppercase small tags above every single title.
   - Do not arbitrarily color one word in a headline with an accent color.
5. **NO Fake Testimonials, Metric Walls, or Placeholder Bloat:**
   - Every metric on screen must correspond to real live telemetry (MT5 balance, equity, drawdowns, spread, win rate, Sharpe ratio).
   - If an element doesn't serve an active trading purpose, remove it.

---

## 2. Typography & Visual Hierarchy

1. **Typography Stack:**
   - Primary: System sans-serif / Inter (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif`).
   - Numerical / Financial: Monospace tabular numbers (`"JetBrains Mono", "SF Mono", "Fira Code", monospace; font-variant-numeric: tabular-nums`).
2. **Type Scale:**
   - Display: 1.25rem - 1.5rem (compact, dense, high information density).
   - Section Heads: 1.0rem - 1.1rem (Semi-bold / 600).
   - Body & Controls: 0.82rem - 0.88rem (Medium / 500).
   - Meta / Subtext: 0.70rem - 0.75rem (Muted / Regular 400).
3. **Contrast & Readability:**
   - Main Text: High contrast `#f8fafc` or `#f1f5f9`.
   - Secondary Text: `#94a3b8`.
   - Muted/Border: `rgba(255, 255, 255, 0.08)`.

---

## 3. Responsive Layout & Ergonomics (All Devices)

1. **Mobile (360px – 640px):**
   - Bottom navigation dock for one-thumb reachability.
   - Sticky top bar with only critical actions (Symbol, Live Price, Quick Buy/Sell).
   - Touch targets must be at least `44px` height on mobile or have adequate hit margins.
   - Zero horizontal scroll (`overflow-x: clip;` on `html` and `body`).
2. **Tablet & Small Laptops (768px – 1024px):**
   - 2-column adaptive layout: Chart on left/top, orders and order book / telemetry on right/bottom.
   - Flexible toolbars that collapse cleanly into popover menus or compact segmented pills.
3. **Desktop (1280px – 1920px+):**
   - Terminal density: Maximize chart canvas area (`min-height: 520px`).
   - Keep toolbars aligned to a strict single-row baseline (~36px - 40px height).
   - Centered and capped containers; gutters expand gracefully on ultra-wide screens.

---

## 4. Interaction & Motion Rules

1. Never use `transition: all`. Specify exact properties: `transition: background-color 0.15s ease, border-color 0.15s ease, opacity 0.15s ease`.
2. Respect `prefers-reduced-motion: reduce`.
3. Provide instant `:focus-visible` feedback on all interactive elements.
