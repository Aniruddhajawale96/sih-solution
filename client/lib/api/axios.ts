import axios, { AxiosError, AxiosInstance } from "axios";
import Constants from "expo-constants";
import useAppStore from "@/store";

/**
 * Base URL
 * Prefer env, fallback for dev
 */
const BASE_URL =
  process.env.EXPO_PUBLIC_API_URL ||
  Constants.expoConfig?.extra?.apiUrl ||
  "http://localhost:8000";

/**
 * Create axios instance
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

/* ------------------------------------------------ */
/* Request Interceptor                              */
/* ------------------------------------------------ */
apiClient.interceptors.request.use(
  (config) => {
    const token = useAppStore.getState().auth?.token;

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error),
);

/* ------------------------------------------------ */
/* Response Interceptor                             */
/* ------------------------------------------------ */
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    /**
     * Centralized error handling
     */
    if (error.response) {
      const status = error.response.status;

      if (status === 401) {
        // Optional: logout user
        useAppStore.getState().logout?.();
      }
    }

    return Promise.reject(error);
  },
);

export default apiClient;
