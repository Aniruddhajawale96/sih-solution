export function extractViewBox(svg: string) {
  const match = svg.match(/viewBox\s*=\s*"([^"]+)"/);
  if (!match) return null;

  const [minX, minY, width, height] = match[1].trim().split(/\s+/).map(Number);

  return { minX, minY, width, height };
}
