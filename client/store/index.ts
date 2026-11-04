import { DEFAULT_SVG } from "@/constants/defaults";
import { AppStore } from "@/types/store";
import { create } from "zustand";

const useAppStore = create<AppStore>((set) => ({
  user: {
    username: "ananta",
    name: "Ananta",
  },
  setUser: (user) => set((state) => ({ user: { ...state.user, ...user } })),

  auth: {
    token: "hf43r4fbvfiu4389vh3498",
  },
  logout: () => null,
  svg: DEFAULT_SVG,
  setSvg: (svg) => {
    set(() => ({ svg }));
  },
  isAuthenticated: false,
  isProfileComplete: false,

  setAuthenticated: (v) => set({ isAuthenticated: v }),
  setProfileComplete: (v) => set({ isProfileComplete: v }),

  registrationNumber: "",
  setRegistrationNumber: (num) => set({ registrationNumber: num }),

  soilType: "clay",
  setSoilType: (soil) => set({ soilType: soil }),

  budget: 0,
  setBudget: (budget: number) => set({ budget }),

  recommendations: {},
  setRecommendations: (recommendations) => set({ recommendations }),
}));

export default useAppStore;
