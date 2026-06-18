import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ToastProvider, useToast } from "./ToastContext";

function Trigger() {
  const toast = useToast();
  return (
    <div>
      <button type="button" onClick={() => toast.success("Saved OK")}>
        fire
      </button>
      <button
        type="button"
        onClick={() => {
          for (let i = 1; i <= 6; i += 1) toast.info(`msg-${i}`);
        }}
      >
        burst
      </button>
    </div>
  );
}

describe("ToastContext", () => {
  // Fake timers so the auto-dismiss setTimeout never fires after unmount.
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("shows a pushed toast and removes it via its close button", () => {
    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>,
    );
    fireEvent.click(screen.getByText("fire"));
    expect(screen.getByText("Saved OK")).toBeInTheDocument();

    const close = screen.getAllByRole("button").find((b) => b.textContent === "×");
    expect(close).toBeDefined();
    fireEvent.click(close as HTMLElement);
    expect(screen.queryByText("Saved OK")).toBeNull();
  });

  it("caps the visible stack at 5, dropping the oldest", () => {
    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>,
    );
    fireEvent.click(screen.getByText("burst"));
    expect(screen.getAllByRole("listitem")).toHaveLength(5);
    expect(screen.queryByText("msg-1")).toBeNull();
    expect(screen.getByText("msg-6")).toBeInTheDocument();
  });

  it("auto-dismisses a toast after its duration elapses", () => {
    render(
      <ToastProvider>
        <Trigger />
      </ToastProvider>,
    );
    fireEvent.click(screen.getByText("fire"));
    expect(screen.getByText("Saved OK")).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(5300);
    });
    expect(screen.queryByText("Saved OK")).toBeNull();
  });
});
