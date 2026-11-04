import { UserLocation } from "@/types/user";
import * as Location from "expo-location";

export async function getUserLocation(): Promise<UserLocation | null> {
  try {
    // Ask permission
    const { status } = await Location.requestForegroundPermissionsAsync();

    if (status !== "granted") {
      console.warn("Location permission not granted");
      return null;
    }

    // Get current location
    const location = await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.High,
    });

    return {
      latitude: location.coords.latitude,
      longitude: location.coords.longitude,
    };
  } catch (error) {
    console.error("Error getting location:", error);
    return null;
  }
}
