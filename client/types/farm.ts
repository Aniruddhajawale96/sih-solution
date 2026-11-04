export type Point = { x: number; y: number };

// GeoJSON-like polygon type used by polygon-clipping
export type Pair = [number, number];
export type Ring = Pair[];
export type Polygon = Ring[];
export type MultiPolygon = Polygon[];

export interface FarmSections {
  name: string;
  area: {
    total: number;
    rowStart: number;
    rowEnd: number;
    columnStart: number;
    columnEnd: number;
  };
  cropSuggestion: {
    name: string;
    estimatedBudget: number;
  };
}
export interface Farm {
  height: number;
  width: number;
  sectionInfo: {
    rows: number;
    column: number;
  };
  sections: FarmSections[];
}

export type SoilType =
  | "red soil"
  | "alluvial"
  | "black soil"
  | "sandy"
  | "clay"
  | "loamy";
