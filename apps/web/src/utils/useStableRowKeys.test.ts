import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useStableRowKeys } from "./useStableRowKeys";

describe("useStableRowKeys", () => {
  it("gives every row a distinct key", () => {
    const { result } = renderHook(() => useStableRowKeys(3));

    const keys = [0, 1, 2].map((i) => result.current.keyAt(i));

    expect(new Set(keys).size).toBe(3);
  });

  it("keeps the same keys across a re-render that does not change the row count", () => {
    // This is the property the focus bug turned on: an edit re-renders with the
    // same number of rows, and the key must not move.
    const { result, rerender } = renderHook(({ n }) => useStableRowKeys(n), {
      initialProps: { n: 2 },
    });
    const before = [result.current.keyAt(0), result.current.keyAt(1)];

    rerender({ n: 2 });

    expect([result.current.keyAt(0), result.current.keyAt(1)]).toEqual(before);
  });

  it("keeps existing keys when a row is appended", () => {
    const { result, rerender } = renderHook(({ n }) => useStableRowKeys(n), {
      initialProps: { n: 2 },
    });
    const before = [result.current.keyAt(0), result.current.keyAt(1)];

    act(() => result.current.noteInsert());
    rerender({ n: 3 });

    expect(result.current.keyAt(0)).toBe(before[0]);
    expect(result.current.keyAt(1)).toBe(before[1]);
  });

  it("gives the appended row a key nobody else has", () => {
    const { result, rerender } = renderHook(({ n }) => useStableRowKeys(n), {
      initialProps: { n: 2 },
    });

    act(() => result.current.noteInsert());
    rerender({ n: 3 });

    const keys = [0, 1, 2].map((i) => result.current.keyAt(i));
    expect(new Set(keys).size).toBe(3);
  });

  it("keeps the surviving rows' keys when a middle row is removed", () => {
    // The improvement over an index key: removing row 0 previously shifted every
    // later row onto a new key, remounting all of them.
    const { result, rerender } = renderHook(({ n }) => useStableRowKeys(n), {
      initialProps: { n: 3 },
    });
    const before = [result.current.keyAt(0), result.current.keyAt(1), result.current.keyAt(2)];

    act(() => result.current.noteRemoval(1));
    rerender({ n: 2 });

    expect(result.current.keyAt(0)).toBe(before[0]);
    expect(result.current.keyAt(1)).toBe(before[2]);
  });

  it("keeps the trailing rows' keys when the first row is removed", () => {
    const { result, rerender } = renderHook(({ n }) => useStableRowKeys(n), {
      initialProps: { n: 3 },
    });
    const before = [result.current.keyAt(0), result.current.keyAt(1), result.current.keyAt(2)];

    act(() => result.current.noteRemoval(0));
    rerender({ n: 2 });

    expect([result.current.keyAt(0), result.current.keyAt(1)]).toEqual([before[1], before[2]]);
  });

  it("regenerates when the document is replaced wholesale", () => {
    // A template load or import is not a row edit: there is no correspondence to keep.
    const { result, rerender } = renderHook(({ n }) => useStableRowKeys(n), {
      initialProps: { n: 2 },
    });
    const before = result.current.keyAt(0);

    rerender({ n: 7 });

    expect(result.current.keyAt(0)).not.toBe(before);
  });

  it("still returns a key for an index beyond the known rows", () => {
    const { result } = renderHook(() => useStableRowKeys(1));

    expect(result.current.keyAt(5)).toBeTruthy();
  });

  it("handles an empty grid", () => {
    const { result } = renderHook(() => useStableRowKeys(0));

    expect(result.current.keyAt(0)).toBeTruthy();
  });
});
