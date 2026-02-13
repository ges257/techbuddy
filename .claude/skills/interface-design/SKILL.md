---
name: interface-design
description: Design engineering for consistent, crafted interfaces. Maintains design consistency using the Warmth & Approachability approach for elderly users.
---

# Interface Design — Warmth & Approachability

Build interface design with craft and consistency. This project targets elderly users (65+).

## Who Is This Human?

An elderly person (65+) who may be confused, frustrated, or embarrassed about needing help with technology. They're at home, possibly alone, and need to feel safe and welcomed.

## What Should This Feel Like?

Warm like a cozy kitchen. Patient like a kind grandchild. Clear like a well-organized desk. Never clinical, never technical, never rushing.

## Design Tokens

```css
--bg-page: #FFF8F0;           /* Warm cream */
--bg-user: #E3F2FD;           /* Soft blue — user messages */
--bg-assistant: #FFF3E0;      /* Warm peach — assistant messages */
--bg-family: #E8F5E9;         /* Soft green — family SMS */
--text-primary: #1a1a1a;      /* Near-black */
--text-secondary: #555;       /* Labels, metadata */
--text-muted: #999;           /* Placeholders only */
--accent-primary: #4CAF50;    /* Friendly green */
--accent-warm: #FF7043;       /* Warm orange */
--border-soft: rgba(0,0,0,0.08);
--shadow-soft: 0 1px 3px rgba(0,0,0,0.08);
--radius-message: 20px;
--radius-button: 12px;
--font-size-body: 20px;
--touch-min: 48px;
--spacing-base: 8px;
```

## Principles

1. **Every element must be obvious.** If it's clickable, it looks clickable.
2. **Warmth over precision.** Soft shadows > hard borders. Rounded > sharp. Cream > pure white.
3. **Breathing room.** Generous padding. White space is a feature.
4. **High contrast text.** 4.5:1 minimum. Dark on light always.
5. **Consistent visual language.** Same radius, shadows, spacing throughout.
6. **Forgiving interactions.** Large touch targets (48px+). Confirm before destructive actions.

## Avoid

- Pure white backgrounds (use warm cream)
- Harsh borders (use soft rgba or shadows)
- Small text (minimum 14px, prefer 18px+)
- Multiple competing accent colors
- Rapid/spinning animations (dizziness risk)
- Technical jargon in any UI text
- Dark mode (elderly prefer light)
- Complex navigation (max 3 steps)
