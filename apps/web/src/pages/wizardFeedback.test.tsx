/**
 * Four wizard defects that all left the user without something the screen owed them.
 *
 * - "Remove" on a component silently deleted every data flow that referenced it. The
 *   cascade is correct — dangling references make the document unvalidatable — but it
 *   happened with no dialog, no toast and no inline message, and data flows are authored
 *   separately on their own step. The only trace was a count changing on step 4.
 * - A duplicate component id produced no inline signal at all while editing, and surfaced
 *   on "Next" as the server's raw verdict at the top of the step, with nothing saying which
 *   row was wrong: "DOCUMENT_VALIDATION_ERROR: … components: Value error, duplicate id in
 *   components".
 * - The three "Context-adaptive questions" selects had no accessible name: no id, no label,
 *   no aria-label, the question text stranded in a sibling paragraph. WCAG 2.1 4.1.2, on
 *   controls whose answers are stored as tags on the exported model.
 * - The semantic-profile input was labelled with the literal i18n-shaped string
 *   "template_semantic_profile", identical in both UI languages, under a summary and help
 *   text that are both translated.
 */

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WizardPage } from "./WizardPage";
import { SessionProvider } from "../context/SessionContext";
import { ToastProvider } from "../context/ToastContext";
import i18n from "../i18n/i18n";
import type { OtmDocument } from "../types/document";

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
    metadata: { title: "Payments Platform", tags: [] },
    components: [
      { id: "web_ui", name: "Customer Web UI", kind: "process" },
      { id: "api", name: "Payments API", kind: "process" },
      { id: "db", name: "Card Vault DB", kind: "datastore" },
    ],
    data_flows: [
      { id: "f_ui_api", from_component: "web_ui", to_component: "api", name: "Checkout request" },
      { id: "f_api_db", from_component: "api", to_component: "db", name: "Store card token" },
    ],
    trust_boundaries: [],
    assets: [],
    threats: [],
    mitigations: [],
    evidence_suggestions: [],
  } as unknown as OtmDocument;
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

async function gotoComponents(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "Next" }));
  await waitFor(() => expect(document.querySelector("#comp-0-id")).not.toBeNull());
}

/** "Remove" on the row at `idx` — the buttons are in document order, one per row. */
async function removeRow(user: ReturnType<typeof userEvent.setup>, idx: number) {
  await user.click(screen.getAllByRole("button", { name: "Remove" })[idx]);
}

beforeEach(async () => {
  await i18n.changeLanguage("en");
  sessionStorage.clear();
  sessionStorage.setItem(DOC_KEY, JSON.stringify(seedDocument()));
});

describe("removing a component that flows reference", () => {
  it("says how many data flows went with it", async () => {
    const user = userEvent.setup();
    render(<WizardPage />, { wrapper: Providers });
    await gotoComponents(user);

    await removeRow(user, 1);

    expect(await screen.findByText(/also deleted 2 data flows/)).toBeInTheDocument();
  });

  it("names the component the user removed", async () => {
    const user = userEvent.setup();
    render(<WizardPage />, { wrapper: Providers });
    await gotoComponents(user);

    await removeRow(user, 1);

    expect(await screen.findByText(/Removing .Payments API./)).toBeInTheDocument();
  });

  it("uses the singular when exactly one flow goes", async () => {
    const user = userEvent.setup();
    render(<WizardPage />, { wrapper: Providers });
    await gotoComponents(user);

    await removeRow(user, 0);

    expect(await screen.findByText(/also deleted 1 data flow that/)).toBeInTheDocument();
  });

  it("still deletes the flows, because leaving them dangling breaks the document", async () => {
    const user = userEvent.setup();
    render(<WizardPage />, { wrapper: Providers });
    await gotoComponents(user);

    await removeRow(user, 1);

    await waitFor(() => expect(storedDoc().data_flows).toHaveLength(0));
  });

  it("says nothing when the component had no flows", async () => {
    const doc = seedDocument();
    doc.data_flows = [];
    sessionStorage.setItem(DOC_KEY, JSON.stringify(doc));
    const user = userEvent.setup();
    render(<WizardPage />, { wrapper: Providers });
    await gotoComponents(user);

    await removeRow(user, 1);

    await waitFor(() => expect(storedDoc().components).toHaveLength(2));
    expect(screen.queryByText(/also deleted/)).toBeNull();
  });
});

describe("a duplicate component id", () => {
  async function makeDuplicate(user: ReturnType<typeof userEvent.setup>) {
    const idInput = document.querySelector<HTMLInputElement>("#comp-1-id")!;
    await user.clear(idInput);
    await user.type(idInput, "web_ui");
  }

  it("is flagged on the offending field while typing, not on Next", async () => {
    const user = userEvent.setup();
    render(<WizardPage />, { wrapper: Providers });
    await gotoComponents(user);

    await makeDuplicate(user);

    expect(document.querySelector("#comp-1-id")).toHaveAttribute("aria-invalid", "true");
  });

  it("explains the collision next to the field", async () => {
    const user = userEvent.setup();
    render(<WizardPage />, { wrapper: Providers });
    await gotoComponents(user);

    await makeDuplicate(user);

    expect(document.querySelector("#comp-1-id-dup-hint")).toHaveTextContent(
      /already used by another component/,
    );
  });

  it("ties the explanation to the field for assistive tech", async () => {
    const user = userEvent.setup();
    render(<WizardPage />, { wrapper: Providers });
    await gotoComponents(user);

    await makeDuplicate(user);

    expect(document.querySelector("#comp-1-id")?.getAttribute("aria-describedby")).toContain(
      "comp-1-id-dup-hint",
    );
  });

  it("clears once the id is unique again", async () => {
    const user = userEvent.setup();
    render(<WizardPage />, { wrapper: Providers });
    await gotoComponents(user);
    await makeDuplicate(user);

    await user.type(document.querySelector<HTMLInputElement>("#comp-1-id")!, "_2");

    expect(document.querySelector("#comp-1-id")).not.toHaveAttribute("aria-invalid");
  });

  it("leaves distinct ids alone", async () => {
    const user = userEvent.setup();
    render(<WizardPage />, { wrapper: Providers });
    await gotoComponents(user);

    expect(document.querySelector("#comp-0-id")).not.toHaveAttribute("aria-invalid");
    expect(document.querySelector("#comp-1-id")).not.toHaveAttribute("aria-invalid");
  });
});

describe("the context-adaptive questions", () => {
  beforeEach(() => {
    const doc = seedDocument();
    doc.model.template_semantic_profile = "internal_admin_portal";
    sessionStorage.setItem(DOC_KEY, JSON.stringify(doc));
  });

  it("gives every select an accessible name", () => {
    render(<WizardPage />, { wrapper: Providers });

    const adaptive = screen.getByText(/Context-adaptive questions/i).closest("details")!;
    const named = within(adaptive)
      .getAllByRole("combobox")
      .filter((el) => (el.getAttribute("aria-labelledby") ?? "") !== "");

    expect(named).toHaveLength(3);
  });

  it("names each select with its own question", () => {
    render(<WizardPage />, { wrapper: Providers });

    expect(
      screen.getByRole("combobox", { name: /privileged actions that require explicit approval/i }),
    ).toBeInTheDocument();
  });

  it("still records the answer on the model", async () => {
    const user = userEvent.setup();
    render(<WizardPage />, { wrapper: Providers });
    const select = screen.getByRole("combobox", {
      name: /privileged actions that require explicit approval/i,
    });

    await user.selectOptions(select, "yes");

    await waitFor(() =>
      expect(storedDoc().metadata.tags).toContain("wz:internal_admin_portal:approval=yes"),
    );
  });
});

describe("the semantic-profile field label", () => {
  it("is not the raw field identifier", () => {
    render(<WizardPage />, { wrapper: Providers });

    expect(screen.queryByText("template_semantic_profile")).toBeNull();
  });

  it("labels the input in English", () => {
    render(<WizardPage />, { wrapper: Providers });

    expect(screen.getByLabelText("Profile identifier")).toHaveAttribute("id", "tprofile");
  });

  it("labels the input in Portuguese", async () => {
    await i18n.changeLanguage("pt-BR");
    render(<WizardPage />, { wrapper: Providers });
    const label = screen.getByLabelText("Identificador do perfil");
    await i18n.changeLanguage("en");

    expect(label).toHaveAttribute("id", "tprofile");
  });
});
