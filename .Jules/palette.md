## 2024-06-18 - Missing Outline Focus States
**Learning:** Native CSS focus on buttons across this app is disabled/hidden, reducing keyboard accessibility unless explicit `:focus-visible` states are manually added to interactive elements.
**Action:** Always verify keyboard accessibility manually by injecting a `:focus-visible` state or adding explicit tab-navigation testing via playwright for new elements.

## 2024-06-18 - Destructive Action Confirmations
**Learning:** Destructive actions across the Zoo MVP, particularly `deleteAnimal` in `AnimalsView.tsx`, did not provide a confirmation prompt before permanently archiving entities.
**Action:** Native `window.confirm` should be implemented on all destructive UI interactions since this project currently lacks a custom modal framework, ensuring a small code footprint for the fix.
