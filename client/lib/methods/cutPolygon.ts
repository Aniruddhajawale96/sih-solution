import { Pair, Point } from "@/types/farm";
import polygonClipping, { MultiPolygon } from "polygon-clipping";

function pointsToPath(
  points: Point[],
  bounds: {
    minX: number;
    maxX: number;
    minY: number;
    maxY: number;
    padding: number;
  },
) {
  const { minX, maxY, padding } = bounds;

  return (
    points
      .map((p, i) => {
        const x = p.x - minX + padding;
        const y = maxY - p.y + padding; // Y flip for SVG
        return `${i === 0 ? "M" : "L"} ${x} ${y}`;
      })
      .join(" ") + " Z"
  );
}

function computeBounds(points: Point[], padding = 10) {
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);

  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  return {
    minX,
    maxX,
    minY,
    maxY,
    padding,
    width: maxX - minX + padding * 2,
    height: maxY - minY + padding * 2,
  };
}

export function generateFarmSVG(
  boundary: Point[],
  zones: Point[][],
  options?: {
    padding?: number;
    colors?: string[];
    stroke?: string;
    strokeWidth?: number;
  },
) {
  const padding = options?.padding ?? 10;
  const colors = options?.colors ?? [];
  const stroke = options?.stroke ?? "#333";
  const strokeWidth = options?.strokeWidth ?? 1;

  // Compute bounds from ALL zones, not just boundary
  const allPoints = zones.flat();
  const bounds = computeBounds(allPoints, padding);

  const zonePaths = zones
    .map((zone, i) => {
      const d = pointsToPath(zone, bounds);
      const fill = colors[i % colors.length] || "transparent";
      const zoneId = `zone-${i + 1}`;

      return `  <path
      id="${zoneId}"
      d="${d}"
      fill="${fill}"
      stroke="${stroke}"
      stroke-width="${strokeWidth}"
    />`;
    })
    .join("\n");

  return `<svg
  width="${bounds.width}"
  height="${bounds.height}"
  viewBox="0 0 ${bounds.width} ${bounds.height}"
  xmlns="http://www.w3.org/2000/svg"
>
${zonePaths}
</svg>`;
}

type XYPoint = {
  x: number;
  y: number;
};

// Geometry helpers
// --------------------

function latLngToXY(
  p: { latitude: number; longitude: number },
  origin: { latitude: number; longitude: number },
): XYPoint {
  const R = 6378137;
  const dLat = ((p.latitude - origin.latitude) * Math.PI) / 180;
  const dLng = ((p.longitude - origin.longitude) * Math.PI) / 180;

  return {
    x: R * dLng * Math.cos((origin.latitude * Math.PI) / 180),
    y: R * dLat,
  };
}

function lineIntersection(
  p1: XYPoint,
  p2: XYPoint,
  p3: XYPoint,
  p4: XYPoint,
): XYPoint | null {
  const x1 = p1.x,
    y1 = p1.y;
  const x2 = p2.x,
    y2 = p2.y;
  const x3 = p3.x,
    y3 = p3.y;
  const x4 = p4.x,
    y4 = p4.y;

  const denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4);
  if (Math.abs(denom) < 1e-9) return null;

  const t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom;
  const u = ((x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)) / denom;

  if (t >= 0 && t <= 1 && u >= 0 && u <= 1) {
    return {
      x: x1 + t * (x2 - x1),
      y: y1 + t * (y2 - y1),
    };
  }

  return null;
}

// --------------------
// Collect intersections
// --------------------

function collectIntersections(
  p1: XYPoint,
  p2: XYPoint,
  boundary: Pair[],
  existingSegments: { start: XYPoint; end: XYPoint }[],
) {
  const hits: { point: XYPoint; t: number }[] = [];

  const dx = p2.x - p1.x;
  const dy = p2.y - p1.y;
  const len2 = dx * dx + dy * dy;
  if (len2 === 0) return hits;

  const projectT = (pt: XYPoint) =>
    ((pt.x - p1.x) * dx + (pt.y - p1.y) * dy) / len2;

  // boundary intersections
  for (let i = 0; i < boundary.length; i++) {
    const b1 = { x: boundary[i][0], y: boundary[i][1] };
    const b2 = {
      x: boundary[(i + 1) % boundary.length][0],
      y: boundary[(i + 1) % boundary.length][1],
    };

    const hit = lineIntersection(p1, p2, b1, b2);
    if (hit) hits.push({ point: hit, t: projectT(hit) });
  }

  // other split lines
  for (const seg of existingSegments) {
    const hit = lineIntersection(p1, p2, seg.start, seg.end);
    if (hit) hits.push({ point: hit, t: projectT(hit) });
  }

  return hits;
}

// --------------------
// MAIN FUNCTION
// --------------------

export function splitFarmByLines(
  boundary: { latitude: number; longitude: number }[],
  lines: { latitude: number; longitude: number }[][],
): XYPoint[][] {
  const origin = boundary[0];

  const boundaryXY: Pair[] = boundary.map((p) => {
    const xy = latLngToXY(p, origin);
    return [xy.x, xy.y];
  });

  let zones: MultiPolygon = [[boundaryXY]];
  const usedSegments: { start: XYPoint; end: XYPoint }[] = [];

  for (const line of lines) {
    if (line.length < 2) continue;

    const p1 = latLngToXY(line[0], origin);
    const p2 = latLngToXY(line[1], origin);

    const hits = collectIntersections(p1, p2, boundaryXY, usedSegments);

    // ❌ Not enough topology to form a section
    if (hits.length < 2) continue;

    hits.sort((a, b) => a.t - b.t);

    const start = hits[0].point;
    const end = hits[hits.length - 1].point;

    usedSegments.push({ start, end });

    const dx = end.x - start.x;
    const dy = end.y - start.y;
    const len = Math.hypot(dx, dy);
    if (len === 0) continue;

    // thin strip
    const thickness = 0.05;
    const ux = (-dy / len) * thickness;
    const uy = (dx / len) * thickness;

    const strip: MultiPolygon = [
      [
        [
          [start.x + ux, start.y + uy],
          [end.x + ux, end.y + uy],
          [end.x - ux, end.y - uy],
          [start.x - ux, start.y - uy],
          [start.x + ux, start.y + uy],
        ],
      ],
    ];

    const next: MultiPolygon = [];

    for (const zone of zones) {
      if (polygonClipping.intersection(zone, strip)?.length) {
        next.push(...polygonClipping.difference(zone, strip));
      } else {
        next.push(zone);
      }
    }

    zones = next;
  }

  // Convert to simple polygons
  return zones.map((poly) => poly[0].map(([x, y]) => ({ x, y })));
}
