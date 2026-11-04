// /lib/api/model.ts
import api from "./axios"; // Adjust based on your API config location

export interface SoilSection {
  section_name: string;
  water_source: string;
  near_water: boolean;
}

export interface FarmRecommendationInput {
  location: {
    latitude: number;
    longitude: number;
  };
  soil_type: string;
  soil_sections: SoilSection[];
  budget: number;
  crop_type: string;
}

export interface CropRecommendation {
  crop: string;
  risk: number;
  budget: number;
}

export interface ExpectedProfit {
  crop: string;
  expected_profit: number;
  risk: number;
  cost: number;
}

export interface RecommendationResponse {
  recommendations: {
    [sectionName: string]: CropRecommendation[];
  };
  expected_profit: {
    [sectionName: string]: ExpectedProfit[];
  };
}

export const getRecommendation = async (
  farmData: FarmRecommendationInput,
): Promise<RecommendationResponse> => {
  try {
    const response = await api.post(
      "/api/v1/model/getRecommendation",
      farmData,
    );
    return response.data;
  } catch (error) {
    console.error("Error getting recommendation:", error);
    throw error;
  }
};
