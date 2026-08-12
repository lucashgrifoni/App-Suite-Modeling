/**
 * The wizard is the core guided-modeling flow and had no unit test at all.
 *
 * Its component and flow rows were keyed on the values being edited
 * (`key={`comp-${c.id}-${c.name}`}`). Every `onChange` wrote the new value into the
 * document, which changed the key, which made React unmount and remount the row —
 * so the input was destroyed mid-edit and focus fell to `<body>`. The field accepted
 * exactly one character per click; naming five components took roughly a hundred
 * clicks. It also broke the flow-ID rename propagation, whose onFocus/onBlur pair
 * cannot survive an element destroyed between the two events.
 *
 * These tests assert the property that actually matters to the user: after typing,
 * the whole string landed AND focus never left the field.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";
import { WizardPage } from "./WizardPage";
import { SessionProvider } from "../context/SessionContext";
import { ToastProvider } from "../context/ToastContext";
import type { OtmDocument } from "../types/document";

// "Next" validates against the API before advancing. The subject here is the wizard's
// own editing behaviour, not the network, so the call is stubbed to succeed.
vi.mock("../api/otmApi", () => ({
  validateDocument: vi.fn().mockResolvedValue({ valid: true }),
}));

const DOC_KEY = "otm.web.document";

function seedDocument(): OtmDocument {
  return {
    model: {
      schema_version: "1.0.0",
      system_type: "web_application",
      industry_sector: "generic",
      methodology: "stride",
    },
    metadata: { title: "Wizard fixture", tags: [] },
    components: [{ id: "api", name: "Api", kind: "process" }],
    data_flows: [{ id: "f_in", from_component: "api", to_component: "api", name: "In" }],
    trust_boundaries: [],
    assets: [],
    threats: [],
    mitigations: [],
    evidence_suggestions: [],
  };
}

function Providers({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <MemoryRouter initialEntries={["/wizard"]}>
      <ToastProvider>
        <SessionProvider>{children}</SessionProvider>
      </ToastProvider>
    </MemoryRouter>
  );
}

/** Click through to the given wizard step (0 = context, 1 = components, 2 = flows). */
async function gotoStep(user: ReturnType<typeof userEvent.setup>, step: number, fieldId: string) {
  for (let i = 0; i < step; i += 1) {
    await user.click(screen.getByRole("button", { name: "Next" }));
  }
  // Advancing awaits the (stubbed) validate call, so the step's fields appear async.
  await waitFor(() => expect(document.querySelector(fieldId)).not.toBeNull());
  return document.querySelector<HTMLInputElement>(fieldId)!;
}

beforeEach(() => {
  sessionStorage.clear();
  sessionStorage.setItem(DOC_KEY, JSON.stringify(seedDocument()));
});

describe("WizardPage keyboard editing", () => {
  it("keeps focus and accepts a whole string in the component name field", async () => {
    const user = userEvent.setup();
    render(<WizardPage />, { wrapper: Providers });
    const nameInput = await gotoStep(user, 1, "#comp-0-name");

    await user.click(nameInput);
    await user.keyboard("Gateway");

    // Re-queried live: if the row remounted, this is a different DOM node.
    const after = document.querySelector<HTMLInputElement>("#comp-0-name")!;
    expect(after.value).toBe("ApiGateway");
    expect(document.activeElement).toBe(after);
  });

  it("keeps focus and accepts a whole string in the component id field", async () => {
    const user = userEvent.setup();
    render(<WizardPage />, { wrapper: Providers });
    const idInput = await gotoStep(user, 1, "#comp-0-id");

    await user.click(idInput);
    await user.keyboard("_gw");

    const after = document.querySelector<HTMLInputElement>("#comp-0-id")!;
    expect(after.value).toBe("api_gw");
    expect(document.activeElement).toBe(after);
  });

  it("keeps focus and accepts a whole string in the flow id field", async () => {
    const user = userEvent.setup();
    render(<WizardPage />, { wrapper: Providers });
    const flowIdInput = await gotoStep(user, 2, "#flow-0-id");

    await user.click(flowIdInput);
    await user.keyboard("_edge");

    const after = document.querySelector<HTMLInputElement>("#flow-0-id")!;
    expect(after.value).toBe("f_in_edge");
    expect(document.activeElement).toBe(after);
  });
});
