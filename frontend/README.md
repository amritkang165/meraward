# MERAWARD — frontend

React 18 + Vite + TypeScript + Tailwind + MapLibre GL JS, deployed on AWS Amplify Hosting.
Mobile-first PWA. **Owner: Amrit.**

## Routes

| Route | Content |
|---|---|
| `/` | Hero + "Find my ward" CTA, live index ticker, how-it-works |
| `/ward` | Map with draggable pin → ward card + Neglect Index gauge |
| `/report` | 3 steps: issue type → photo → review bilingual draft (EN/HI tabs, editable) |
| `/dashboard` | Full map + heatmap toggle, leaderboard, filters |
| `/c/:id` | Complaint detail: photo, bilingual draft, status timeline |
| `/u/:token` | Magic-link status update |
| `/about` | Data provenance, sources, licences, index methodology |

## Notes

- Amplify needs an SPA rewrite (`/<*>` → `/index.html`) or every deep link 404s.
- Record and test the demo on **Android Chrome**.
