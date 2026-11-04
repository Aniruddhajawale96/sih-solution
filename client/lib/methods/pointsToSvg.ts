import { Point } from "@/types/farm";

export function pointsToSVG(
  points: Point[],
  options?: {
    padding?: number;
    fill?: string;
    stroke?: string;
    strokeWidth?: number;
  },
) {
  if (points.length < 2) {
    throw new Error("At least 2 points required");
  }

  const padding = options?.padding ?? 10;
  const fill = options?.fill ?? "none";
  const stroke = options?.stroke ?? "black";
  const strokeWidth = options?.strokeWidth ?? 2;

  // 1️⃣ Calculate bounds
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);

  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  const width = maxX - minX + padding * 2;
  const height = maxY - minY + padding * 2;

  // 2️⃣ Flip Y for SVG
  const path =
    points
      .map((p, i) => {
        const x = p.x - minX + padding;
        const y = maxY - p.y + padding; // 🔥 Y FLIP HERE
        return `${i === 0 ? "M" : "L"} ${x} ${y}`;
      })
      .join(" ") + " Z";

  // 3️⃣ SVG output
  return `
<svg
  width="${width}"
  height="${height}"
  viewBox="0 0 ${width} ${height}"
  xmlns="http://www.w3.org/2000/svg"
>
  <path
    d="${path}"
    fill="${fill}"
    stroke="${stroke}"
    stroke-width="${strokeWidth}"
  />
</svg>
`.trim();
}
