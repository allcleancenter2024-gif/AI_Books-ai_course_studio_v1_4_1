# v1.27.1 — 2026-09-13

## Workspace layout and UI

- Added a four-lane workspace overview: 준비, 수집·검토, 제작·출판, 운영·안전.
- Added direct jump cards for the recommended course-production flow without changing existing section IDs or API behavior.
- Improved the side navigation with a persistent overview entry, active-step styling, keyboard focus treatment, and responsive card layout.
- Added mobile and reduced-motion behavior for the new overview components.

## Verification

- Full regression suite: 116 passed.
- Python compile check and `git diff --check` passed.
