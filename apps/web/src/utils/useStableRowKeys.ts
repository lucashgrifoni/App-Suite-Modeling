import { useRef } from "react";

/**
 * Durable React keys for an editable grid whose rows carry no stable identity.
 *
 * The wizard's rows live in `doc.components` / `doc.data_flows`, and every edit
 * replaces the whole array (`{...doc, components}`), so the row objects cannot be
 * used as identity. Neither can their contents: `id` and `name` are precisely the
 * fields being typed into, and keying on them made React unmount the row on every
 * keystroke — the input was destroyed mid-edit and focus fell to `<body>`, so the
 * field accepted one character per click.
 *
 * A row key must therefore be minted once and follow the row for as long as it
 * exists. This hook keeps a key per row position and, crucially, *splices* rather
 * than regenerating: removing row 0 keeps row 1's key, so the surviving rows are
 * not remounted either.
 *
 * The document can also be replaced wholesale from outside the grid — a template,
 * an import, a history restore. Those are not row edits and there is no row-level
 * correspondence to preserve, so a length change that did not come from
 * `insertedAt`/`removedAt` regenerates the keys.
 */

let counter = 0;

function mintKey(): string {
  counter += 1;
  return `row-${counter}`;
}

function mintKeys(count: number): string[] {
  return Array.from({ length: count }, mintKey);
}

export interface RowKeys {
  /** Key for the row currently at `index`. */
  keyAt: (index: number) => string;
  /** Call when a row is appended, so existing rows keep their keys. */
  noteInsert: () => void;
  /** Call when the row at `index` is removed, so the rows after it keep theirs. */
  noteRemoval: (index: number) => void;
}

export function useStableRowKeys(count: number): RowKeys {
  const keys = useRef<string[]>(mintKeys(count));

  // Reconciliation happens during render because the key is needed *now*. It is a
  // ref, not state, so this schedules no extra render.
  if (keys.current.length !== count) {
    keys.current = mintKeys(count);
  }

  return {
    keyAt: (index) => keys.current[index] ?? mintKey(),
    noteInsert: () => {
      keys.current = [...keys.current, mintKey()];
    },
    noteRemoval: (index) => {
      keys.current = keys.current.filter((_, i) => i !== index);
    },
  };
}
