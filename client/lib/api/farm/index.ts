import apiClient from "../axios";

interface FarmBoundaryParam {
  formattedBoundary: {
    latitude: number;
    longitude: number;
  }[];
}
export const setFarmBoundary = async ({
  formattedBoundary,
}: FarmBoundaryParam) => {
  const res = await apiClient.post("/api/v1/farm/boundary", {
    farm_id: "farm123",
    boundary: formattedBoundary,
  });

  return res.data;
};
