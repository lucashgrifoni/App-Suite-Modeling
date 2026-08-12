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
import { ApiError } from "../api/client";
import { validateDocument } from "../api/otmApi";
import { SessionProvider } from "../context/SessionContext";
import { ToastProvider } from "../context/ToastContext";
import i18n from "../i18n/i18n";
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
    trust_boundaries: [{ id: "tb", name: "TB", member_component_ids: ["api"] }],
    assets: [{ id: "asset_1", name: "Asset", related_component_ids: ["api"] }],
    threats: [],
    mitigations: [],
    evidence_suggestions: [],
  };
}

function storedDoc(): OtmDocument {
  return JSON.parse(sessionStorage.getItem(DOC_KEY)!) as OtmDocument;
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

/**
 * These assert the WIRING, not the helpers. `nextEntityId` and `applyComponentIdRename`
 * have their own unit tests in utils/wizardEdits.test.ts, but a tested helper that no
 * component calls fixes nothing for the user — so these drive the real inputs and buttons.
 */
describe("WizardPage document integrity", () => {
  it("propagates a component id rename to flows, assets and boundaries on blur", async () => {
    const user = userEvent.setup();
    render(<WizardPage />, { wrapper: Providers });
    const idInput = await gotoStep(user, 1, "#comp-0-id");

    await user.click(idInput);
    await user.keyboard("_gw");
    await user.tab(); // blur is what commits the rename

    await waitFor(() => expect(storedDoc().components[0].id).toBe("api_gw"));
    const saved = storedDoc();
    expect(saved.data_flows[0].from_component).toBe("api_gw");
    expect(saved.data_flows[0].to_component).toBe("api_gw");
    expect(saved.assets[0].related_component_ids).toEqual(["api_gw"]);
    expect(saved.trust_boundaries[0].member_component_ids).toEqual(["api_gw"]);
  });

  it("never mints a component id that already exists", async () => {
    const user = userEvent.setup();
    render(<WizardPage />, { wrapper: Providers });
    await gotoStep(user, 1, "#comp-0-id");

    // Add two, remove the first, add again. Length-based ids hand back `comp_2` twice.
    await user.click(screen.getByRole("button", { name: /add component/i }));
    await user.click(screen.getByRole("button", { name: /add component/i }));
    const removeButtons = screen.getAllByRole("button", { name: /remove/i });
    await user.click(removeButtons[1]);
    await user.click(screen.getByRole("button", { name: /add component/i }));

    const ids = storedDoc().components.map((c) => c.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});

/**
 * `template_semantic_profile` trimmed inside `onChange`, so the controlled input was fed
 * back its own trimmed value and the space the user had just typed vanished before the next
 * character arrived. "api backend rest" came out "apibackendrest", with no hint anywhere on
 * the page that spaces were unwelcome.
 */
describe("WizardPage template_semantic_profile field", () => {
  async function profileField(user: ReturnType<typeof userEvent.setup>) {
    render(<WizardPage />, { wrapper: Providers });
    // The field lives inside a collapsed <details> disclosure on step 1.
    await user.click(screen.getByText("Template semantic profile (optional)"));
    return document.querySelector<HTMLInputElement>("#tprofile")!;
  }

  it("keeps the spaces the user types", async () => {
    const user = userEvent.setup();
    const field = await profileField(user);

    await user.click(field);
    await user.keyboard("api backend rest");

    expect(document.querySelector<HTMLInputElement>("#tprofile")!.value).toBe(
      "api backend rest",
    );
  });

  it("keeps leading spaces while the user is still typing", async () => {
    const user = userEvent.setup();
    const field = await profileField(user);

    await user.click(field);
    await user.keyboard("  leading");

    expect(document.querySelector<HTMLInputElement>("#tprofile")!.value).toBe("  leading");
  });

  it("trims on blur, which is when the value is committed", async () => {
    const user = userEvent.setup();
    const field = await profileField(user);

    await user.click(field);
    await user.keyboard("  api_backend  ");
    await user.tab();

    await waitFor(() => expect(storedDoc().model.template_semantic_profile).toBe("api_backend"));
  });

  it("commits a whitespace-only entry as no profile at all", async () => {
    const user = userEvent.setup();
    const field = await profileField(user);

    await user.click(field);
    await user.keyboard("   ");
    await user.tab();

    await waitFor(() => expect(storedDoc().model.template_semantic_profile).toBeNull());
  });
});

/**
 * Step gating was component-local state initialised to 0, so arriving at /wizard with a
 * finished model in session — or simply refreshing — re-locked Components, Flows and Finish.
 * Editing an existing model's components meant clicking "Next" through steps that had
 * nothing left to ask, and the step tabs looked like navigation while being dead.
 */
describe("WizardPage step unlocking", () => {
  function stepButton(name: RegExp): HTMLButtonElement {
    return screen.getByRole("button", { name }) as HTMLButtonElement;
  }

  it("unlocks the components step for a model that already has components", () => {
    render(<WizardPage />, { wrapper: Providers });
    expect(stepButton(/2\. Components/)).toBeEnabled();
  });

  it("unlocks the flows step for a model that already has flows", () => {
    render(<WizardPage />, { wrapper: Providers });
    expect(stepButton(/3\. Flows/)).toBeEnabled();
  });

  it("unlocks the finish step for a model that already has flows", () => {
    render(<WizardPage />, { wrapper: Providers });
    expect(stepButton(/4\. Finish/)).toBeEnabled();
  });

  it("keeps the components step locked for a model with nothing in it yet", () => {
    sessionStorage.setItem(
      DOC_KEY,
      JSON.stringify({ ...seedDocument(), components: [], data_flows: [] }),
    );
    render(<WizardPage />, { wrapper: Providers });
    expect(stepButton(/2\. Components/)).toBeDisabled();
  });

  it("does not re-lock the steps ahead when the user steps back", async () => {
    const user = userEvent.setup();
    render(<WizardPage />, { wrapper: Providers });
    await user.click(stepButton(/4\. Finish/));

    await user.click(stepButton(/1\. Context/));

    expect(stepButton(/4\. Finish/)).toBeEnabled();
  });

  it("returns to the step the user was on after a remount", async () => {
    const user = userEvent.setup();
    const first = render(<WizardPage />, { wrapper: Providers });
    await user.click(stepButton(/3\. Flows/));
    await waitFor(() => expect(document.querySelector("#flow-0-id")).not.toBeNull());
    first.unmount();

    render(<WizardPage />, { wrapper: Providers });

    expect(document.querySelector("#flow-0-id")).not.toBeNull();
  });

  it("ignores a stored step the current model cannot support", () => {
    // A blank model must not open on "Flows" just because the previous model was finished.
    sessionStorage.setItem("otm.web.wizard.step", "3");
    sessionStorage.setItem(
      DOC_KEY,
      JSON.stringify({ ...seedDocument(), components: [], data_flows: [] }),
    );

    render(<WizardPage />, { wrapper: Providers });

    expect(screen.getByLabelText("Model title")).toBeInTheDocument();
  });

  it("ignores a corrupt stored step", () => {
    sessionStorage.setItem("otm.web.wizard.step", "not-a-number");

    render(<WizardPage />, { wrapper: Providers });

    expect(screen.getByLabelText("Model title")).toBeInTheDocument();
  });
});

/**
 * The ID field on a component row is trimmed on blur; the Name field beside it was not.
 * A name of three spaces was therefore stored verbatim and travelled into every deliverable:
 * the Mermaid export rendered `p2["   "]` as an empty box and the Markdown export emitted
 * `- **   ** (`p2`) — process`, where the bold markers wrap only spaces and print as literal
 * asterisks in most renderers. Nothing in the wizard said a word about it.
 */
describe("WizardPage component name normalisation", () => {
  it("does not store a name that is only whitespace", async () => {
    const user = userEvent.setup();
    render(<WizardPage />, { wrapper: Providers });
    const nameInput = await gotoStep(user, 1, "#comp-0-name");

    await user.clear(nameInput);
    await user.type(nameInput, "   ");
    await user.tab();

    expect(storedDoc().components[0].name.trim()).not.toBe("");
  });

  it("falls back to the component id, the one label guaranteed to exist", async () => {
    const user = userEvent.setup();
    render(<WizardPage />, { wrapper: Providers });
    const nameInput = await gotoStep(user, 1, "#comp-0-name");

    await user.clear(nameInput);
    await user.type(nameInput, "   ");
    await user.tab();

    expect(storedDoc().components[0].name).toBe("api");
  });

  it("trims the padding off a real name instead of discarding it", async () => {
    const user = userEvent.setup();
    render(<WizardPage />, { wrapper: Providers });
    const nameInput = await gotoStep(user, 1, "#comp-0-name");

    await user.clear(nameInput);
    await user.type(nameInput, "  Gateway  ");
    await user.tab();

    expect(storedDoc().components[0].name).toBe("Gateway");
  });

  it("leaves a name that needs no normalisation exactly as typed", async () => {
    const user = userEvent.setup();
    render(<WizardPage />, { wrapper: Providers });
    const nameInput = await gotoStep(user, 1, "#comp-0-name");

    await user.clear(nameInput);
    await user.type(nameInput, "Payments API");
    await user.tab();

    expect(storedDoc().components[0].name).toBe("Payments API");
  });
});

/**
 * Clearing a component ID produced, on screen, `components.0.id: String should match pattern
 * '^[a-zA-Z0-9_][a-zA-Z0-9_.-]*$'` — Pydantic's raw regex plus a 0-based path that matches
 * nothing the user can see. The rule behind that pattern is one sentence long.
 */
describe("WizardPage validation errors", () => {
  function schemaRejection() {
    return new ApiError(
      "DOCUMENT_VALIDATION_ERROR: The document does not satisfy the canonical schema.",
      422,
      {
        detail: {
          code: "DOCUMENT_VALIDATION_ERROR",
          message: "The document does not satisfy the canonical schema.",
          errors: [
            {
              loc: ["body", "components", 0, "id"],
              msg: "String should match pattern '^[a-zA-Z0-9_][a-zA-Z0-9_.-]*$'",
            },
          ],
        },
      },
      true,
    );
  }

  it("does not show the raw schema regex to the user", async () => {
    const user = userEvent.setup();
    vi.mocked(validateDocument).mockRejectedValueOnce(schemaRejection());
    render(<WizardPage />, { wrapper: Providers });

    await user.click(screen.getByRole("button", { name: "Next" }));

    await waitFor(() => expect(screen.getByRole("alert")).not.toHaveTextContent("a-zA-Z0-9_"));
  });

  it("states the id rule in words instead", async () => {
    const user = userEvent.setup();
    vi.mocked(validateDocument).mockRejectedValueOnce(schemaRejection());
    render(<WizardPage />, { wrapper: Providers });

    await user.click(screen.getByRole("button", { name: "Next" }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(i18n.t("apiErrors.entityIdPattern")),
    );
  });

  it("points at the component row the way the UI numbers it", async () => {
    const user = userEvent.setup();
    vi.mocked(validateDocument).mockRejectedValueOnce(schemaRejection());
    render(<WizardPage />, { wrapper: Providers });

    await user.click(screen.getByRole("button", { name: "Next" }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("components[1].id"));
  });
});
