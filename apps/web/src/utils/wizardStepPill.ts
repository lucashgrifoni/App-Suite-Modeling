export function stepPillClass(currentStep: number, index: number): string {
  if (index === currentStep) return "bg-slate-900 text-white";
  if (index < currentStep) return "bg-slate-200 text-slate-800";
  return "bg-slate-100 text-slate-400";
}

