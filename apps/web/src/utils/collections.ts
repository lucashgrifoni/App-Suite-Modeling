export function updateArrayItem<T>(items: T[], index: number, nextItem: T): T[] {
  return items.map((item, i) => (i === index ? nextItem : item));
}

export function removeArrayItem<T>(items: T[], index: number): T[] {
  return items.filter((_, i) => i !== index);
}

