import apiClient from "../axios";

interface LatLng {
    latitude: number;
    longitude: number;
}

interface FarmVisitCheckParams {
    boundary: LatLng[];
    user_location: LatLng;
    image_count: number;
    gps_accuracy: number;
}

export const checkFarmVisit = async ({
    boundary,
    user_location,
    image_count,
    gps_accuracy,
}: FarmVisitCheckParams) => {
    const res = await apiClient.post("/api/v1/farm/visit/visit/check", {
        farm_id: "farm123", // temp
        boundary,
        user_location,
        image_count,
        gps_accuracy,
    });

    return res.data;
};
