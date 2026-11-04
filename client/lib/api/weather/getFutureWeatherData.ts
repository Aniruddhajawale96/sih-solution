import axios from "axios";

const API_KEY = process.env.EXPO_PUBLIC_WEATHER_API_KEY;
const BASE_URL = "http://api.weatherapi.com/v1";

export const getFutureWeatherData = async () => {
  const res = await axios.get(`${BASE_URL}/future.json`, {
    params: {
      key: API_KEY, // 🔑 API key here
      q: "Delhi", // city / lat,long
      days: 300, // future days
    },
  });

  return res.data;
};
