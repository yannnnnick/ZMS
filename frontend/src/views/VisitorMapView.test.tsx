import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { VisitorMapView } from "./VisitorMapView";
import type { PublicZooMap } from "../types";

describe("VisitorMapView", () => {
  it("renders null or empty state when publicMap is null", () => {
    render(<VisitorMapView publicMap={null} />);
    expect(screen.getByText("Lade Karte...")).toBeInTheDocument();
  });

  it("renders the map and enclosures when publicMap is provided", () => {
    const mockMap: PublicZooMap = {
      enclosures: [
        {
          public_name: "Löwengehege",
          location: "Süd",
          public_description: "Großes Gehege für die Löwen",
          map_x: 100,
          map_y: 100,
          map_width: 200,
          map_height: 150,
          animals: [
            { name: "Simba", species: "Löwe", sex: "male", age_years: 5 }
          ]
        },
        {
          public_name: "Affenhaus",
          location: "Nord",
          public_description: null,
          map_x: 400,
          map_y: 100,
          map_width: 150,
          map_height: 150,
          animals: []
        }
      ],
      paths: [
        { from_enclosure: "Löwengehege", to_enclosure: "Affenhaus" }
      ]
    };

    render(<VisitorMapView publicMap={mockMap} />);

    // Title should be present
    expect(screen.getByText("Besucherkarte")).toBeInTheDocument();

    // Map enclosures (using getAllByText since it appears in map and detail list)
    expect(screen.getAllByText("Löwengehege")[0]).toBeInTheDocument();
    expect(screen.getAllByText("Affenhaus")[0]).toBeInTheDocument();

    // Animal counts
    expect(screen.getByText("1 Tiere")).toBeInTheDocument();
    expect(screen.getByText("0 Tiere")).toBeInTheDocument();

    // Detail section
    expect(screen.getByText("Großes Gehege für die Löwen")).toBeInTheDocument();
    expect(screen.getByText(/Simba - Löwe/)).toBeInTheDocument();
  });

  it("handles missing enclosures in paths gracefully without crashing", () => {
    const mockMap: PublicZooMap = {
      enclosures: [
        {
          public_name: "Löwengehege",
          location: "Süd",
          public_description: null,
          map_x: 100,
          map_y: 100,
          map_width: 200,
          map_height: 150,
          animals: []
        }
      ],
      paths: [
        // Refers to non-existent 'Affenhaus'
        { from_enclosure: "Löwengehege", to_enclosure: "Affenhaus" }
      ]
    };

    const { container } = render(<VisitorMapView publicMap={mockMap} />);

    // Map should still render Löwengehege
    expect(screen.getAllByText("Löwengehege")[0]).toBeInTheDocument();

    // But no line for the path should be drawn (because 'Affenhaus' is missing)
    const lines = container.querySelectorAll("line");
    expect(lines.length).toBe(0);
  });
});
