import axios from "axios";

/**
 * ENV
 */
const API_KEY = process.env.EXPO_PUBLIC_WEATHER_API_KEY;
const BASE_URL = "https://api.weatherapi.com/v1";
const MAX_SEVERITY_SCORE = 3;
/**
 * TYPES
 */
export interface WorstWeatherDay {
  date: string;
  severity: number;
  condition: string;
  avgTempC: number;
  maxWindKph: number;
  totalPrecipMm: number;
  humidity: number;
  uv: number;
}

/**
 * Generate future dates between 14–300 days
 * step = 3 means 1 API call every 3 days (cost + rate-limit safe)
 */
const generateFutureDates = (
  startOffset = 14,
  endOffset = 300,
  step = 2,
): string[] => {
  const dates: string[] = [];
  const today = new Date();

  for (let i = startOffset; i <= endOffset; i += step) {
    const d = new Date(today);
    d.setDate(today.getDate() + i);
    dates.push(d.toISOString().split("T")[0]);
  }

  return dates;
};

type FutureWeatherParams = {
  dt: string;
  location?: { latitude: number; longitude: number };
};
/**
 * Fetch future weather for ONE date
 */
const fetchFutureWeather = async ({ dt, location }: FutureWeatherParams) => {
  const res = await axios.get(`${BASE_URL}/future.json`, {
    params: {
      key: API_KEY,
      q: location
        ? `${location.latitude},${location.longitude}`
        : "Cherrapunji, India", // 🔁 change city if needed
      dt,
    },
  });

  return res.data.forecast.forecastday[0];
};

/**
 * Compute severity score (custom logic)
 */
const computeSeverityScore = (day: any): number => {
  let score = 0;

  // 🌧️ Heavy rain / snow
  if (day.day.totalprecip_mm >= 30) score += 3;
  else if (day.day.totalprecip_mm >= 10) score += 2;

  // 💨 Strong winds
  if (day.day.maxwind_kph >= 50) score += 3;
  else if (day.day.maxwind_kph >= 30) score += 2;

  // 🌡️ Extreme temperature
  if (day.day.avgtemp_c >= 45 || day.day.avgtemp_c <= -5) score += 3;
  else if (day.day.avgtemp_c >= 40) score += 2;

  // 💧 High humidity
  if (day.day.avghumidity >= 90) score += 1;

  // ☀️ High UV
  if (day.day.uv >= 9) score += 1;

  return score;
};

/**
 * MAIN FUNCTION
 * Returns sorted worst weather days
 */
export const getWorstWeatherNext300Days = async (location?: {
  latitude: number;
  longitude: number;
}): Promise<WorstWeatherDay[]> => {
  const dates = generateFutureDates();
  const worstDays: WorstWeatherDay[] = [];

  for (const dt of dates) {
    try {
      const forecast = await fetchFutureWeather({ dt, location });
      const severity = computeSeverityScore(forecast);

      // Only keep "bad" days
      if (severity >= MAX_SEVERITY_SCORE) {
        worstDays.push({
          date: forecast.date,
          severity,
          condition: forecast.day.condition.text,
          avgTempC: forecast.day.avgtemp_c,
          maxWindKph: forecast.day.maxwind_kph,
          totalPrecipMm: forecast.day.totalprecip_mm,
          humidity: forecast.day.avghumidity,
          uv: forecast.day.uv,
        });
      }
    } catch (err) {
      console.warn(`Failed to fetch weather for ${dt}`, err);
    }
  }

  // Sort by worst first
  return worstDays.sort((a, b) => b.severity - a.severity);
};
