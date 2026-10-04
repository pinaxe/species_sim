// Fixed categorical palette for species series (map dots, chart lines/bars).
// Dark-mode steps of the validated default categorical order -- this app is
// always dark-themed (bg-slate-900), so we use that column directly.
// Colors are assigned by a species' position in the config's species array,
// which is stable regardless of filtering, per the "color follows the entity"
// rule.
export const SPECIES_COLORS = [
  '#3987e5', // slot 1 - blue
  '#d95926', // slot 2 - orange
  '#199e70', // slot 3 - aqua
  '#c98500', // slot 4 - yellow
  '#d55181', // slot 5 - magenta
  '#008300', // slot 6 - green
  '#9085e9', // slot 7 - violet
  '#e66767', // slot 8 - red
];

export function speciesColor(index: number): string {
  return SPECIES_COLORS[index % SPECIES_COLORS.length];
}
