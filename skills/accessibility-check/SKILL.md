# Accessibility Check

Review any user-facing code (HTML, CSS, JSX, TSX, Python templates) for elderly accessibility compliance.

## Checklist
- Font size >= 18px (no small text anywhere)
- Touch/click targets >= 48px
- Color contrast ratio >= 4.5:1
- Plain language only — no jargon, no technical terms
- Max 3 steps to complete any action
- Voice input and TTS always available
- Confirm before: sending, deleting, financial actions
- Error messages are friendly and actionable ("Something went wrong. Let's try again." not stack traces)

## How to Use
When reviewing code, check each item above. Flag violations with the specific line and what needs to change. Suggest fixes in elderly-friendly language.

## Example Violations
- `font-size: 14px` → must be at least 18px
- `button { width: 30px }` → must be at least 48px
- `color: #999 on #fff` → contrast too low (2.8:1), use #595959 or darker
- "Error 403: Forbidden" → "We couldn't complete that. Let's try again."
- 5-step wizard → simplify to 3 steps max
