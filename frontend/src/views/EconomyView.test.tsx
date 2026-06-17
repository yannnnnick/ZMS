import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EconomyView } from "./EconomyView";
import { api } from "../api";
import type { Animal, EconomySummary, FeedingOptimization, SalarySimulation, Session, User } from "../types";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    api: {
      ...actual.api,
      salarySimulation: vi.fn(),
      feedingOptimization: vi.fn()
    }
  };
});

const salarySimulationMock = vi.mocked(api.salarySimulation);
const feedingOptimizationMock = vi.mocked(api.feedingOptimization);

const adminSession: Session = { role: "admin", display_name: "Ada", csrf_token: "csrf" };

const mockUsers: User[] = [
  { id: 1, email: "john@zoo.com", display_name: "John Doe", role: "keeper", is_active: true }
];

const mockAnimals: Animal[] = [
  {
    id: 1,
    name: "Leo",
    species_id: 1,
    enclosure_id: 1,
    sex: "male",
    health_status: "healthy",
    active: true,
    created_at: "",
    updated_at: "",
    species: { id: 1, common_name: "Lion", category: "Mammal" },
    enclosure: { id: 1, name: "Lion Enclosure", location: "North", capacity: 5, safety_status: "ok", is_public_visible: true }
  }
];

const mockEconomy: EconomySummary = {
  visitors_today: 150,
  visitors_week: 1200,
  ticket_revenue_week: 2500000,
  estimated_payroll_month: 4500000,
  food_inventory_value: 500000,
  open_tasks: 12,
  open_vet_cases: 3,
  visitor_stats: [
    { date: "2023-10-01", visitor_count: 100, ticket_revenue: 200000 },
    { date: "2023-10-02", visitor_count: 200, ticket_revenue: 400000 }
  ]
};

describe("EconomyView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders nothing if economy is null", () => {
    const { container } = render(
      <EconomyView session={adminSession} economy={null} users={mockUsers} animals={mockAnimals} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders economy statistics correctly", () => {
    render(
      <EconomyView session={adminSession} economy={mockEconomy} users={mockUsers} animals={mockAnimals} />
    );

    expect(screen.getByText("Besucher heute")).toBeInTheDocument();
    expect(screen.getByText("150")).toBeInTheDocument();
    expect(screen.getByText("Besucher Woche")).toBeInTheDocument();
    expect(screen.getByText("1200")).toBeInTheDocument();
    expect(screen.getByText("Ticketumsatz Woche")).toBeInTheDocument();
    expect(screen.getByText("25.000,00 EUR")).toBeInTheDocument();
    expect(screen.getByText("Personalkosten Monat")).toBeInTheDocument();
    expect(screen.getByText("45.000,00 EUR")).toBeInTheDocument();
    expect(screen.getByText("Offene Vet-Faelle")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("submits salary simulation and displays results", async () => {
    const mockSalaryResult: SalarySimulation = {
      user: mockUsers[0],
      hours: 40,
      hourly_rate: 2000,
      gross_pay: 80000,
      estimated_deductions: 20000,
      estimated_net: 60000,
      is_simulation: true
    };
    salarySimulationMock.mockResolvedValue(mockSalaryResult as never);

    render(
      <EconomyView session={adminSession} economy={mockEconomy} users={mockUsers} animals={mockAnimals} />
    );

    const selects = screen.getAllByRole("combobox");
    const userCombobox = selects[0]; // First one is users, second is animals

    await userEvent.selectOptions(userCombobox, "1");

    // Change dates to ensure onChange handlers are covered
    // Since there are no labels, we'll get all inputs and find the date ones.
    const container = screen.getByText("Berechnen").closest("form");
    const inputs = container?.querySelectorAll('input[type="date"]') as NodeListOf<HTMLInputElement>;
    const startDateInput = inputs[0];
    const endDateInput = inputs[1];

    await userEvent.clear(startDateInput);
    await userEvent.type(startDateInput, "2023-11-01");

    await userEvent.clear(endDateInput);
    await userEvent.type(endDateInput, "2023-11-30");

    await userEvent.click(screen.getByRole("button", { name: "Berechnen" }));

    expect(salarySimulationMock).toHaveBeenCalledWith(
      "csrf",
      expect.objectContaining({ user_id: 1, start_date: "2023-11-01", end_date: "2023-11-30" })
    );

    // Assert results are shown
    expect(await screen.findByText("40 Stunden")).toBeInTheDocument();
    expect(screen.getAllByText("John Doe").length).toBeGreaterThan(0);
    expect(screen.getByText("Brutto 800,00 EUR")).toBeInTheDocument();
    expect(screen.getByText("Netto geschaetzt 600,00 EUR")).toBeInTheDocument();
  });

  it("submits feeding optimization and displays results", async () => {
    const mockOptimizationResult: FeedingOptimization = {
      success: true,
      message: "Optimierung erfolgreich",
      method: "Linear Programming",
      total_cost: 15000,
      feeding_plan: [
        { food_item_id: 1, food_name: "Meat", quantity: 5, unit: "kg", cost: 15000 }
      ]
    };
    feedingOptimizationMock.mockResolvedValue(mockOptimizationResult as never);

    render(
      <EconomyView session={adminSession} economy={mockEconomy} users={mockUsers} animals={mockAnimals} />
    );

    const selects = screen.getAllByRole("combobox");
    const animalCombobox = selects[1]; // Second select is for animals

    await userEvent.selectOptions(animalCombobox, "1");
    await userEvent.click(screen.getByRole("button", { name: "Optimieren" }));

    expect(feedingOptimizationMock).toHaveBeenCalledWith(
      "csrf",
      expect.objectContaining({ animal_id: 1 })
    );

    expect(await screen.findByText("Optimierung erfolgreich")).toBeInTheDocument();
    expect(screen.getByText("Methode: Linear Programming")).toBeInTheDocument();
    expect(screen.getByText("Gesamtkosten: 150,00 EUR")).toBeInTheDocument();
    expect(screen.getByText("Meat")).toBeInTheDocument();
    expect(screen.getByText("5 kg")).toBeInTheDocument();
    expect(screen.getByText("150,00 EUR")).toBeInTheDocument();
  });
});
