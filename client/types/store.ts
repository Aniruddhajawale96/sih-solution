import { CropRecommendation } from "@/lib/api/model";
import { SoilType } from "./farm";
import { User } from "./user";

export type Recommendations = {
  [sectionName: string]: CropRecommendation[];
};
export interface AppStore {
  user: User;
  setUser: (user: User) => void;

  auth: {
    token: string;
  };
  logout: () => void;

  svg: string;
  setSvg: (svg: string) => void;

  isAuthenticated: boolean;
  isProfileComplete: boolean;

  setAuthenticated: (v: boolean) => void;
  setProfileComplete: (v: boolean) => void;

  registrationNumber: string;
  setRegistrationNumber: (num: string) => void;

  soilType: SoilType;
  setSoilType: (soil: SoilType) => void;

  budget: number;
  setBudget: (budget: number) => void;

  recommendations: Recommendations;
  setRecommendations: (recommendations: Recommendations) => void;
}
