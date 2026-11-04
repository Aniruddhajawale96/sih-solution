import axios from "axios";

/**
 * ENV
 */
const API_KEY = process.env.EXPO_PUBLIC_WEATHER_API_KEY;
const BASE_URL = "https://api.weatherapi.com/v1";

/**
 * UI SEVERITY
 */
export type AlertSeverity = "info" | "warning" | "critical";

export interface WeatherAlertUI {
  id: string;
  title: string;
  message: string;
  severity: AlertSeverity;
}

/**
 * Fetch 14-day forecast
 */
const fetchForecast14Days = async (location?: {
  latitude: number;
  longitude: number;
}) => {
  const res = await axios.get(`${BASE_URL}/forecast.json`, {
    params: {
      key: API_KEY,
      q: location
        ? `${location.latitude},${location.longitude}`
        : "Cherrapunji, India",
      days: 14,
      alerts: "no",
      aqi: "no",
    },
  });

  //   console.log(res);
  return res.data.forecast.forecastday;
};

/**
 * Compute severity score
 */
const computeSeverityScore = (day: any): number => {
  let score = 0;

  if (day.day.totalprecip_mm >= 30) score += 3;
  else if (day.day.totalprecip_mm >= 10) score += 2;

  if (day.day.maxwind_kph >= 50) score += 3;
  else if (day.day.maxwind_kph >= 30) score += 2;

  if (day.day.avgtemp_c >= 45 || day.day.avgtemp_c <= -5) score += 3;
  else if (day.day.avgtemp_c >= 40) score += 2;

  if (day.day.avghumidity >= 90) score += 1;
  if (day.day.uv >= 9) score += 1;

  return score;
};

/**
 * MAIN FUNCTION (READY TO USE)
 */
export const getWeatherAlerts = async (location?: {
  latitude: number;
  longitude: number;
}): Promise<WeatherAlertUI[]> => {
  try {
    const forecastDays = await fetchForecast14Days(location);

    return forecastDays
      .map((day: any) => {
        const severityScore = computeSeverityScore(day);

        if (severityScore < 3) return null;

        let severity: AlertSeverity = "info";
        let title = "Weather Advisory";
        let message = "Unfavourable weather conditions expected.";

        if (severityScore >= 6) {
          severity = "critical";
          title = "Severe Weather Alert";
        } else if (severityScore >= 1) {
          severity = "warning";
          title = "Weather Warning";
        }

        if (day.day.totalprecip_mm >= 30) {
          message = `Heavy rain expected (${day.day.totalprecip_mm} mm). Avoid irrigation and field work.`;
        } else if (day.day.maxwind_kph >= 50) {
          message = `Strong winds up to ${day.day.maxwind_kph} km/h. Secure crops and equipment.`;
        } else if (day.day.avgtemp_c >= 40) {
          message = `High temperature (${day.day.avgtemp_c}°C). Increase irrigation frequency.`;
        }

        return {
          id: day.date,
          title,
          message,
          severity,
        };
      })
      .filter(Boolean) as WeatherAlertUI[];
  } catch (err) {
    console.error("Weather alert fetch failed", err);
    return [];
  }
};
