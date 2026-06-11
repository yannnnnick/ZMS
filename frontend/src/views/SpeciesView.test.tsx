import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SpeciesView } from "./SpeciesView";
import { api, ApiError } from "../api";
import type { Session } from "../types";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return { ...actual, api: { ...actual.api, createSpecies: vi.fn() } };
});

const createSpeciesMock = vi.mocked(api.createSpecies);
const adminSession: Session = { role: "admin", display_name: "Ada", csrf_token: "csrf" };

describe("SpeciesView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("creates a species and reloads on success", async () => {
    createSpeciesMock.mockResolvedValue({ id: 9 } as never);
    const reload = vi.fn().mockResolvedValue(undefined);

    render(<SpeciesView session={adminSession} species={[]} reload={reload} />);
    await userEvent.type(screen.getByPlaceholderText("Name der Art"), "Rotluchs");
    await userEvent.click(screen.getByRole("button", { name: /Speichern/i }));

    expect(createSpeciesMock).toHaveBeenCalledWith("csrf", expect.objectContaining({ common_name: "Rotluchs" }));
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("surfaces an error and does not reload when the API rejects", async () => {
    createSpeciesMock.mockRejectedValue(new ApiError(409, "Art existiert bereits"));
    const reload = vi.fn().mockResolvedValue(undefined);

    render(<SpeciesView session={adminSession} species={[]} reload={reload} />);
    await userEvent.type(screen.getByPlaceholderText("Name der Art"), "Rotluchs");
    await userEvent.click(screen.getByRole("button", { name: /Speichern/i }));

    expect(await screen.findByText("Art existiert bereits")).toBeInTheDocument();
    expect(reload).not.toHaveBeenCalled();
  });

  it("hides the creation form for non-admin roles", () => {
    const keeperSession: Session = { role: "keeper", display_name: "Kai", csrf_token: "csrf" };
    render(<SpeciesView session={keeperSession} species={[]} reload={vi.fn()} />);

    expect(screen.queryByPlaceholderText("Name der Art")).not.toBeInTheDocument();
  });
});
