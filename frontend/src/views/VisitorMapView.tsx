import { useMemo } from "react";
import { Panel } from "../components/Panel";
import type { PublicEnclosure, PublicZooMap } from "../types";

function centerOf(enclosure: PublicEnclosure) {
  return {
    x: enclosure.map_x + enclosure.map_width / 2,
    y: enclosure.map_y + enclosure.map_height / 2
  };
}

export function VisitorMapView({ publicMap }: { publicMap: PublicZooMap | null }) {
  const enclosureByName = useMemo(() => {
    const lookup = new Map<string, PublicEnclosure>();
    publicMap?.enclosures.forEach((enclosure) => lookup.set(enclosure.public_name, enclosure));
    return lookup;
  }, [publicMap]);

  if (!publicMap) return <div>Lade Karte...</div>;

  return (
    <div className="view-stack">
      <Panel title="Besucherkarte" icon="map">
        <div className="map-shell">
          <svg className="zoo-map" viewBox="0 0 860 520" role="img" aria-label="Interaktive Zoo-Karte">
            <rect className="map-ground" x="20" y="20" width="820" height="480" rx="8" />
            {publicMap.paths.map((path) => {
              const from = enclosureByName.get(path.from_enclosure);
              const to = enclosureByName.get(path.to_enclosure);
              if (!from || !to) return null;
              const start = centerOf(from);
              const end = centerOf(to);
              return <line className="map-path" key={`${path.from_enclosure}-${path.to_enclosure}`} x1={start.x} y1={start.y} x2={end.x} y2={end.y} />;
            })}
            {publicMap.enclosures.map((enclosure) => (
              <g className="map-enclosure" key={enclosure.public_name}>
                <rect x={enclosure.map_x} y={enclosure.map_y} width={enclosure.map_width} height={enclosure.map_height} rx="8" />
                <text x={enclosure.map_x + 14} y={enclosure.map_y + 28}>
                  {enclosure.public_name}
                </text>
                <text className="map-small" x={enclosure.map_x + 14} y={enclosure.map_y + 52}>
                  {enclosure.animals.length} Tiere
                </text>
              </g>
            ))}
          </svg>
        </div>
      </Panel>

      <section className="map-detail-grid">
        {publicMap.enclosures.map((enclosure) => (
          <article className="map-detail-card" key={enclosure.public_name}>
            <strong>{enclosure.public_name}</strong>
            <span>{enclosure.location}</span>
            {enclosure.public_description ? <p>{enclosure.public_description}</p> : null}
            <div className="animal-tags">
              {enclosure.animals.map((animal) => (
                <span key={`${enclosure.public_name}-${animal.name}`}>
                  {animal.name} - {animal.species}
                  {animal.age_years ? `, ${animal.age_years} Jahre` : ""}
                </span>
              ))}
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
