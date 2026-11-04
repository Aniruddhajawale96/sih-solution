export type AlertSeverity = "info" | "warning" | "critical";

export interface WeatherAlert {
  id: string;
  title: string;
  message: string;
  severity: AlertSeverity;
  type?: "rain" | "temperature" | "wind" | "storm" | "humidity";
  location?: string;
  timestamp?: string; // ISO string
}

export const MOCK_WEATHER_ALERTS: WeatherAlert[] = [
  {
    id: "1",
    title: "Heavy Rain Alert",
    message:
      "Heavy rainfall expected in the next 24 hours. Ensure proper drainage to avoid waterlogging in fields.",
    severity: "warning",
    type: "rain",
    location: "Pune, Maharashtra",
    timestamp: "2026-02-06T05:30:00Z",
  },
  {
    id: "2",
    title: "Extreme Heat Warning",
    message:
      "Day temperatures may rise above 40°C. Increase irrigation frequency to protect crops from heat stress.",
    severity: "critical",
    type: "temperature",
    location: "Nagpur, Maharashtra",
    timestamp: "2026-02-06T03:15:00Z",
  },
  {
    id: "3",
    title: "Strong Wind Advisory",
    message:
      "Strong winds expected. Secure greenhouse structures and support tall crops like sugarcane.",
    severity: "warning",
    type: "wind",
    location: "Ahmedabad, Gujarat",
    timestamp: "2026-02-05T22:10:00Z",
  },
  {
    id: "4",
    title: "Favorable Weather Conditions",
    message:
      "Weather conditions are optimal for wheat growth. Ideal time for fertilizer application.",
    severity: "info",
    type: "temperature",
    location: "Ludhiana, Punjab",
    timestamp: "2026-02-05T18:45:00Z",
  },
  {
    id: "5",
    title: "High Humidity Alert",
    message:
      "High humidity levels detected. Monitor crops for early signs of fungal diseases.",
    severity: "warning",
    type: "humidity",
    location: "Kochi, Kerala",
    timestamp: "2026-02-06T01:00:00Z",
  },
  {
    id: "6",
    title: "Thunderstorm Warning",
    message:
      "Thunderstorms with lightning expected tonight. Avoid field work during storm hours.",
    severity: "critical",
    type: "storm",
    location: "Ranchi, Jharkhand",
    timestamp: "2026-02-06T06:00:00Z",
  },
];
