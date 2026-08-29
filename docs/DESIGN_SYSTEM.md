# LegalIA Design System

LegalIA is a calm, professional workspace for legal research and drafting. The interface should make the next useful action obvious, preserve the user's sense of control, and keep legal context visible without exposing implementation details.

## Intent

- Make legal work feel focused, trustworthy, and familiar.
- Use a light, ChatGPT/LibreChat-inspired shell with restrained surfaces and minimal chrome.
- Apply Apple's principles of purpose, agency, familiarity, flexibility, simplicity, craft, and accessible feedback.
- Preserve dark mode and functional density for research-heavy workflows.

## Visual principles

1. **Calm hierarchy:** one primary action, quiet secondary actions, and clear grouping.
2. **Neutral surfaces:** warm-white application background, soft gray panels, charcoal text, and muted slate controls. Accent color is reserved for focus, selection, and meaningful status.
3. **Content first:** conversation, document identity, and legal context outrank decoration and telemetry.
4. **Material with restraint:** use translucency only for floating chrome, never as stacked decorative glass.
5. **Familiar controls:** compact icon buttons, readable labels, predictable placement, and visible focus states.

## Tokens

The source of truth is `frontend/src/index.css`. Components must consume semantic tokens rather than inventing one-off colors.

| Role | Light direction | Usage |
| --- | --- | --- |
| `--bg-app` | white | Main workspace |
| `--bg-sidebar` | soft neutral | Navigation and side panels |
| `--bg-surface` | white | Cards, menus, composer |
| `--bg-surface-hover` | light gray | Hover and quiet emphasis |
| `--text-primary` | charcoal | Headings and body text |
| `--text-secondary` | slate | Supporting copy |
| `--text-muted` / `--text-dim` | muted slate | Hints and low-priority labels |
| `--border-subtle` / `--border-medium` | cool neutral | Separation and control boundaries |
| `--border-focus` | accessible slate | Keyboard and input focus |
| `--action-primary` | deep slate | Primary actions |

Technical telemetry (tokens, reduction percentages, provider internals, and processing statistics) is not user-facing unless it is directly needed for an action.

## Typography

Use the platform system stack first: `system-ui`, `-apple-system`, and compatible sans-serif fallbacks. Body text should use comfortable leading (approximately 1.45–1.65). Headings use weight and size together, with modest negative tracking at display sizes. Avoid all-caps micro-labels; sentence case is the default.

## Spacing, radii, and shadows

- Base spacing is `0.25rem`; compose layouts in multiples of the spacing unit.
- Use `--radius-sm` for controls, `--radius-md` for cards, and `--radius-lg` for sheets and modals.
- Reserve capsule radii for compact controls and composer affordances, not every card.
- Use `--shadow-sm` for raised controls, `--shadow-md` for panels, and `--shadow-lg` for modals/popovers.
- Prefer borders plus subtle elevation over oversized cards or dramatic gradients.

## Component rules

- **Shell:** sidebar and sidepanel establish navigation; the chat area remains the visual priority.
- **Chat/composer:** keep the input spacious, actions compact, and attached files above the text field. Show upload progress and errors in plain language.
- **Messages:** use readable measure, restrained metadata, and actions that appear when useful. Keep verification status and citations when they help legal judgment.
- **Files:** show filename, document type, jurisdiction, relevant parties, radicado, clauses, preview, and upload/error status. Do not expose conversion engine names, token counts, savings, percentages, or internal provider details.
- **Forms/options:** present one decision at a time where possible, make the current step clear, support keyboard navigation, and validate inline.
- **Panels and menus:** group related actions, keep controls compact, and avoid redundant badges.

## Interaction, motion, and accessibility

- Give feedback on pointer-down and preserve clear hover, active, disabled, and focus-visible states.
- Use short, critically damped transitions for ordinary UI; reserve bounce for momentum-driven gestures.
- Enter and exit along the same spatial path. Never block input solely because a transition is running.
- Maintain WCAG-conscious contrast, 44px touch targets where practical, semantic labels, and keyboard access.
- Honor `prefers-reduced-motion: reduce` with opacity/color changes instead of movement.
- Honor `prefers-reduced-transparency: reduce` by using solid surfaces and removing blur.
- Honor `prefers-contrast: more` with stronger borders and near-solid surfaces.

## Responsive behavior

- Desktop uses a narrow navigation rail, optional sidepanel, and centered conversation measure.
- At mobile widths, sidepanels become fixed overlays, controls remain reachable, and cards/actions wrap without horizontal scrolling.
- Preserve content order and focus order across breakpoints. Do not hide essential actions behind hover-only behavior on touch devices.

## Content principles

- Lead with the action or outcome, not implementation language.
- Prefer specific, plain-language labels: “Ver vista previa”, “Quitar archivo”, and “Analizar cláusulas”.
- Keep meaningful legal context; remove redundant metadata and engineering jargon.
- Explain errors in terms of what the user can do next.
- Technical telemetry is internal by default: tokens, reduction percentages, provider names, processing stats, and conversion internals stay hidden unless directly required for an action.

## Explicitly out of scope

- Backend, API, parser, upload, export, or data-model changes.
- Replacing the existing icon system or copying LibreChat source code/assets.
- Decorative terracotta or saturated-blue branding accents.
- Exposing model/provider internals, token economics, or processing telemetry in ordinary user flows.
- Adding new animations, gamification, badges, or ornamental cards without a demonstrated user benefit.
