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
const adminSession: Session = { role: "admin", display_name: "Ada", csrf_token: "csrf" };
const vetSession: Session = { role: "vet", display_name: "Val", csrf_token: "csrf" };

const mockSpecies: Species[] = [{ id: 1, common_name: "Lion", scientific_name: "Panthera leo", conservation_status: "vulnerable" }];
const mockEnclosures: Enclosure[] = [{ id: 1, name: "Savanna", type: "savanna", capacity: 5, maintenance_status: "good", biome: "grassland" }];
const mockAnimals: Animal[] = [];
const mockAnimalsWithItems: Animal[] = [
  {
    id: 1,
    name: "Simba",
    species: mockSpecies[0],
    enclosure: mockEnclosures[0],
    birth_date: "2018-05-01",
    age_years: 5,
    sex: "male",
    health_status: "healthy",
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
        animals={mockAnimals}
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

  it("updates an animal's health status and reloads", async () => {
    const updateAnimalMock = vi.mocked(api.updateAnimal);
    updateAnimalMock.mockResolvedValue(true as never);
    const reload = vi.fn().mockResolvedValue(undefined);

    render(
      <AnimalsView
        session={adminSession}
        species={mockSpecies}
        enclosures={mockEnclosures}
        animals={mockAnimalsWithItems}
        reload={reload}
      />
    );

    const user = userEvent.setup();
    const select = screen.getByRole("combobox", { name: `Gesundheitsstatus fuer Simba` });

    await user.selectOptions(select, "treatment");

    expect(updateAnimalMock).toHaveBeenCalledWith("csrf", 1, { health_status: "treatment" });
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("deletes an animal and reloads", async () => {
    const deleteAnimalMock = vi.mocked(api.deleteAnimal);
    deleteAnimalMock.mockResolvedValue(true as never);
    const reload = vi.fn().mockResolvedValue(undefined);

    render(
      <AnimalsView
        session={adminSession}
        species={mockSpecies}
        enclosures={mockEnclosures}
        animals={mockAnimalsWithItems}
        reload={reload}
      />
    );

    const user = userEvent.setup();
    const deleteButton = screen.getByRole("button", { name: /Archivieren/i });

    await user.click(deleteButton);

    expect(deleteAnimalMock).toHaveBeenCalledWith("csrf", 1);
    expect(reload).toHaveBeenCalledTimes(1);
  });
});
