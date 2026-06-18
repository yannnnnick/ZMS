import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AnimalsView } from "./AnimalsView";
import { api, ApiError } from "../api";
import type { Session, Species, Enclosure, Animal } from "../types";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return { ...actual, api: { ...actual.api, createAnimal: vi.fn(), updateAnimal: vi.fn(), deleteAnimal: vi.fn() } };
});

const createAnimalMock = vi.mocked(api.createAnimal);
const updateAnimalMock = vi.mocked(api.updateAnimal);
const deleteAnimalMock = vi.mocked(api.deleteAnimal);

const adminSession: Session = { role: "admin", display_name: "Ada", csrf_token: "csrf" };
const vetSession: Session = { role: "vet", display_name: "Val", csrf_token: "csrf" };
const viewerSession: Session = { role: "viewer", display_name: "Vi", csrf_token: "csrf" };

const mockSpecies: Species[] = [
  { id: 1, common_name: "Lion", scientific_name: "Panthera leo", category: "mammal", conservation_status: "vulnerable" }
];
const mockEnclosures: Enclosure[] = [
  { id: 1, name: "Savanna", location: "North", capacity: 5, safety_status: "ok", is_public_visible: true }
];
const mockAnimals: Animal[] = [
  {
    id: 1,
    name: "Leo",
    species_id: 1,
    enclosure_id: 1,
    birth_date: "2020-01-01",
    sex: "male",
    health_status: "healthy",
    active: true,
    created_at: "2020-01-01T00:00:00Z",
    updated_at: "2020-01-01T00:00:00Z",
    age_years: 6,
    species: mockSpecies[0],
    enclosure: mockEnclosures[0]
  },
  {
    id: 2,
    name: "UnknownAge",
    species_id: 1,
    enclosure_id: 1,
    birth_date: null,
    sex: "unknown",
    health_status: "observation",
    active: true,
    created_at: "2020-01-01T00:00:00Z",
    updated_at: "2020-01-01T00:00:00Z",
    age_years: null,
    species: mockSpecies[0],
    enclosure: mockEnclosures[0]
  }
];

describe("AnimalsView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(window, "confirm").mockReturnValue(true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("creates an animal and reloads on success", async () => {
    createAnimalMock.mockResolvedValue({ id: 1 } as never);
    const reload = vi.fn().mockResolvedValue(undefined);

    render(
      <AnimalsView
        session={adminSession}
        species={mockSpecies}
        enclosures={mockEnclosures}
        animals={mockAnimals}
        reload={reload}
      />
    );

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText("Name"), "Leo");
    await user.selectOptions(screen.getByRole("combobox", { name: "Art" }), "1");
    await user.selectOptions(screen.getByRole("combobox", { name: "Gehege" }), "1");
    // birth_date is hard to test cross-browser, we'll try it with string format. Note standard userEvent.type might have trouble with date inputs depending on the browser environment. Wait, JS DOM handles it fine. Let's omit it for simpler test since it's not required, or type in a valid format.
    await user.type(screen.getByLabelText("Geburtsdatum"), "2020-01-01");
    await user.selectOptions(screen.getByRole("combobox", { name: "Geschlecht" }), "male");

    await user.click(screen.getByRole("button", { name: /Anlegen/i }));

    expect(createAnimalMock).toHaveBeenCalledWith("csrf", expect.objectContaining({
      name: "Leo",
      species_id: 1,
      enclosure_id: 1,
      birth_date: "2020-01-01",
      sex: "male"
    }));
    expect(reload).toHaveBeenCalledTimes(1);
    expect(screen.getByPlaceholderText("Name")).toHaveValue("");
    expect(screen.getByRole("combobox", { name: "Art" })).toHaveValue("");
    expect(screen.getByRole("combobox", { name: "Gehege" })).toHaveValue("");
    expect(screen.getByLabelText("Geburtsdatum")).toHaveValue("");
    expect(screen.getByRole("combobox", { name: "Geschlecht" })).toHaveValue("unknown");
  });

  it("creates an animal without birth date and sends null", async () => {
    createAnimalMock.mockResolvedValue({ id: 2 } as never);
    const reload = vi.fn().mockResolvedValue(undefined);

    render(
      <AnimalsView
        session={adminSession}
        species={mockSpecies}
        enclosures={mockEnclosures}
        animals={[]}
        reload={reload}
      />
    );

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText("Name"), "Nala");
    await user.selectOptions(screen.getByRole("combobox", { name: "Art" }), "1");
    await user.selectOptions(screen.getByRole("combobox", { name: "Gehege" }), "1");
    await user.selectOptions(screen.getByRole("combobox", { name: "Geschlecht" }), "female");

    await user.click(screen.getByRole("button", { name: /Anlegen/i }));

    expect(createAnimalMock).toHaveBeenCalledWith("csrf", expect.objectContaining({
      name: "Nala",
      species_id: 1,
      enclosure_id: 1,
      birth_date: null,
      sex: "female"
    }));
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("surfaces an error and does not reload when the API rejects", async () => {
    createAnimalMock.mockRejectedValue(new ApiError(400, "Invalid data"));
    const reload = vi.fn().mockResolvedValue(undefined);

    render(
      <AnimalsView
        session={adminSession}
        species={mockSpecies}
        enclosures={mockEnclosures}
        animals={mockAnimals}
        reload={reload}
      />
    );

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText("Name"), "Leo");
    await user.selectOptions(screen.getByRole("combobox", { name: "Art" }), "1");
    await user.selectOptions(screen.getByRole("combobox", { name: "Gehege" }), "1");

    await user.click(screen.getByRole("button", { name: /Anlegen/i }));

    expect(await screen.findByText("Invalid data")).toBeInTheDocument();
    expect(reload).not.toHaveBeenCalled();
  });

  it("hides the creation form for vet roles", () => {
    render(
      <AnimalsView
        session={vetSession}
        species={mockSpecies}
        enclosures={mockEnclosures}
        animals={mockAnimals}
        reload={vi.fn()}
      />
    );

    expect(screen.queryByPlaceholderText("Name")).not.toBeInTheDocument();
  });

  it("renders animal list with fallbacks for missing age and birth date", () => {
    render(
      <AnimalsView
        session={adminSession}
        species={mockSpecies}
        enclosures={mockEnclosures}
        animals={mockAnimals}
        reload={vi.fn()}
      />
    );

    expect(screen.getByText("6 Jahre")).toBeInTheDocument();
    expect(screen.getByText("unknown")).toBeInTheDocument();
  });

  it("updates animal health status and reloads on success", async () => {
    updateAnimalMock.mockResolvedValue({ id: 1 } as never);
    const reload = vi.fn().mockResolvedValue(undefined);

    render(
      <AnimalsView
        session={vetSession}
        species={mockSpecies}
        enclosures={mockEnclosures}
        animals={mockAnimals}
        reload={reload}
      />
    );

    const user = userEvent.setup();
    await user.selectOptions(screen.getByRole("combobox", { name: "Gesundheitsstatus fuer Leo" }), "treatment");

    expect(updateAnimalMock).toHaveBeenCalledWith("csrf", 1, { health_status: "treatment" });
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("shows an error and does not reload when health update fails", async () => {
    updateAnimalMock.mockRejectedValue(new ApiError(500, "Update failed"));
    const reload = vi.fn().mockResolvedValue(undefined);

    render(
      <AnimalsView
        session={vetSession}
        species={mockSpecies}
        enclosures={mockEnclosures}
        animals={mockAnimals}
        reload={reload}
      />
    );

    const user = userEvent.setup();
    await user.selectOptions(screen.getByRole("combobox", { name: "Gesundheitsstatus fuer Leo" }), "treatment");

    expect(await screen.findByText("Update failed")).toBeInTheDocument();
    expect(reload).not.toHaveBeenCalled();
  });

  it("deletes an animal and reloads on success when user is admin", async () => {
    deleteAnimalMock.mockResolvedValue(true as never);
    const reload = vi.fn().mockResolvedValue(undefined);

    render(
      <AnimalsView
        session={adminSession}
        species={mockSpecies}
        enclosures={mockEnclosures}
        animals={mockAnimals}
        reload={reload}
      />
    );

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Tier Leo archivieren" }));

    expect(deleteAnimalMock).toHaveBeenCalledWith("csrf", 1);
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("shows an error and does not reload when deleting an animal fails", async () => {
    deleteAnimalMock.mockRejectedValue(new ApiError(500, "Deletion failed"));
    const reload = vi.fn().mockResolvedValue(undefined);

    render(
      <AnimalsView
        session={adminSession}
        species={mockSpecies}
        enclosures={mockEnclosures}
        animals={mockAnimals}
        reload={reload}
      />
    );

    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Tier Leo archivieren" }));

    expect(await screen.findByText("Deletion failed")).toBeInTheDocument();
    expect(reload).not.toHaveBeenCalled();
  });

  it("hides health and archive actions for viewers", () => {
    render(
      <AnimalsView
        session={viewerSession}
        species={mockSpecies}
        enclosures={mockEnclosures}
        animals={mockAnimals}
        reload={vi.fn()}
      />
    );

    expect(screen.queryByRole("combobox", { name: "Gesundheitsstatus fuer Leo" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Tier Leo archivieren" })).not.toBeInTheDocument();
  });
});
