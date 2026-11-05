# Phase 4A.1 UX audit — recorded before implementation

2026-11-05, `thesis/ui-demo`, inherited uncommitted Phase 4A at `e3bde80`.
Reviewed AGENTS.md, the Phase 4A report, all frontend pages/components, models,
adapter, state, bridge types and styles. No Python changes are planned.

Measured the production UI using installed Edge at 1366×768. Before screenshots
and raw measurements are preserved in `frontend/qa/phase4a1/before/`.

| Screen | Document height | Measured problem |
| --- | ---: | --- |
| Dashboard | 909 px | Composition is sound; 9–11 px metadata, redundant preview indicators and marketing headings weaken clarity. Main cards are visible. Preserve composition. |
| Sign | 997 px | 207 px dropzone; all three steps expanded. Unlock at y=677–699, signing preview at y=836–877. Large paper illustration exists before selection. Repeated disclosures consume header space. |
| Verify | 1049 px | 207 px dropzone; public keys follow it and the preview action is at y=911–952. Empty results occupy nearly the same area as populated results. |
| Vault | 902 px | Unlock at y=655–693; password and backup at y=767–805. Storage/education compete with the key ID and primary action. |
| Settings | 849 px | Tall theme previews and an oversized About card; 9–11 px explanations. Settings can be more concise without removing functionality. |

Cross-cutting findings: non-sticky topbar; document-level scrolling moves the
breadcrumb away; dozens of one-off small font sizes; repeated global/page/card
preview badges; inconsistent metadata, button and heading sizes. Eliminating
scroll through smaller text would worsen readability. A valid PDF header is
only a selection check, not evidence of a signed PDF.

Implementation decisions:

1. Preserve branding, dashboard two-card composition and existing React/Radix
   components. Add shared density/type/spacing tokens and targeted desktop styles.
2. Use one main scrolling work area beneath a stable topbar. Portal task actions
   into a shell footer outside that scroll area so long content cannot hide them.
3. Signing has one expanded step, collapsed summaries, editable earlier steps
   and clear continuation. The actual Sign PDF action is always disabled while
   native signing is unavailable. Keep a separately labelled UI rehearsal and
   JSON summary; never show a purported cryptographic success or PDF download.
4. Verification keeps compact document/key fields together. Put scenario examples
   behind explicit disclosure; selecting a file never populates valid results.
   Keep actual verification unavailable and example execution explicitly labelled.
5. Place vault Unlock/Lock and management operations at the top. Show public ID
   and status first; move explanatory material into a concise security panel.
6. Use 28–32 px page headings, 18 px section headings, 14 px body/control text and
   at least 12 px meaningful metadata. Retain natural scrolling for real content.
7. Preserve existing functional/security test purposes, adapting copy and step
   navigation assertions to the intentional UX change. Add reachability tests
   before production edits. Test 1280×720, 1366×768, 1600×900, 1920×1080 and an
   effective 1093×614 viewport as an approximation of 1366×768 at 125% scaling.

Physical Windows display scaling, native pywebview behavior and actual PDF
rendering remain unverified; browser viewport/DPR emulation is not an OS test.
