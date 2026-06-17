import { beforeEach, describe, expect, it, vi } from "vitest";
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

const mockSpecies: Species[] = [{ id: 1, common_name: "Lion", scientific_name: "Panthera leo", conservation_status: "vulnerable" }];
const mockEnclosures: Enclosure[] = [{ id: 1, name: "Savanna", type: "savanna", capacity: 5, maintenance_status: "good", biome: "grassland" }];
const mockAnimals: Animal[] = [
  {
    id: 1,
    name: "Leo",
    species_id: 1,
    enclosure_id: 1,
    birth_date: "2015-01-01",
    age_years: 9,
    sex: "male",
    health_status: "healthy",
    species: mockSpecies[0],
    enclosure: mockEnclosures[0]
  },
  {
    id: 2,
    name: "UnknownAge",
    species_id: 1,
    enclosure_id: 1,
    birth_date: null,
    age_years: null,
    sex: "unknown",
    health_status: "sick",
    species: mockSpecies[0],
    enclosure: mockEnclosures[0]
  }
];

describe("AnimalsView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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

    // Check if form was reset
    expect(screen.getByPlaceholderText("Name")).toHaveValue("");
  });

  it("creates an animal with omitted optional fields (birth_date as null)", async () => {
    createAnimalMock.mockResolvedValue({ id: 1 } as never);
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

    // Do not set birth date

    await user.click(screen.getByRole("button", { name: /Anlegen/i }));

    expect(createAnimalMock).toHaveBeenCalledWith("csrf", expect.objectContaining({
      name: "Nala",
      species_id: 1,
      enclosure_id: 1,
      birth_date: null,
      sex: "unknown"
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

  it("renders animal list with correct fallbacks for age/birth date/sex", () => {
    render(
      <AnimalsView
        session={adminSession}
        species={mockSpecies}
        enclosures={mockEnclosures}
        animals={mockAnimals}
        reload={vi.fn()}
      />
    );

    // Leo has age_years
    expect(screen.getByText("9 Jahre")).toBeInTheDocument();

    // UnknownAge has no age_years or birth_date, so fallback to sex
    expect(screen.getByText("unknown")).toBeInTheDocument();
  });

  it("updates an animal's health status via the list row", async () => {
    updateAnimalMock.mockResolvedValue(true as never);
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
    const select = screen.getByRole("combobox", { name: "Gesundheitsstatus fuer Leo" });

    await user.selectOptions(select, "observation");

    expect(updateAnimalMock).toHaveBeenCalledWith("csrf", 1, { health_status: "observation" });
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("deletes an animal via the list row", async () => {
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
    // Assuming there are multiple delete buttons, we want the one for Leo
    const deleteButtons = screen.getAllByTitle("Archivieren");
    await user.click(deleteButtons[0]);

    expect(deleteAnimalMock).toHaveBeenCalledWith("csrf", 1);
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("shows an error and does not reload if row action (update) fails", async () => {
    updateAnimalMock.mockRejectedValue(new ApiError(500, "Update failed"));
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
    const select = screen.getByRole("combobox", { name: "Gesundheitsstatus fuer Leo" });

    await user.selectOptions(select, "observation");

    expect(await screen.findByText("Update failed")).toBeInTheDocument();
    expect(reload).not.toHaveBeenCalled();
  });

  it("shows an error and does not reload if row action (delete) fails", async () => {
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
    const deleteButtons = screen.getAllByTitle("Archivieren");
    await user.click(deleteButtons[0]);

    expect(await screen.findByText("Deletion failed")).toBeInTheDocument();
    expect(reload).not.toHaveBeenCalled();
  });

  it("hides health patch and archive actions for viewers", () => {
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
    expect(screen.queryByTitle("Archivieren")).not.toBeInTheDocument();
  });
});
