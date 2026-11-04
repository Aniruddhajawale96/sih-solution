import { StyleSheet, Text, View } from "react-native";
import React from "react";
import Animated, {
  FadeInUp,
  FadeOutUp,
  LinearTransition,
} from "react-native-reanimated";

type CropInfo = {
  name: string;
  season: string;
  water: string;
  duration: string;
};

const CropInfoCard = ({ crop }: { crop: CropInfo }) => {
  return (
    <Animated.View
      layout={LinearTransition.springify().damping(18)}
      entering={FadeInUp.duration(250)}
      exiting={FadeOutUp.duration(200)}
      style={styles.container}
    >
      <Text style={styles.title}>🌾 {crop.name}</Text>

      <View style={styles.row}>
        <Text style={styles.label}>Season</Text>
        <Text style={styles.value}>{crop.season}</Text>
      </View>

      <View style={styles.row}>
        <Text style={styles.label}>Water</Text>
        <Text style={styles.value}>{crop.water}</Text>
      </View>

      <View style={styles.row}>
        <Text style={styles.label}>Duration</Text>
        <Text style={styles.value}>{crop.duration}</Text>
      </View>
    </Animated.View>
  );
};

export default CropInfoCard;

const styles = StyleSheet.create({
  container: {
    position: "absolute",
    top: 80, // stays below status/header
    left: 16,
    right: 16,
    backgroundColor: "#1E1E1E",
    borderRadius: 16,
    padding: 16,
    elevation: 10, // Android shadow
    shadowColor: "#000", // iOS shadow
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
  },
  title: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 12,
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 6,
  },
  label: {
    color: "#9E9E9E",
    fontSize: 13,
  },
  value: {
    color: "#E0E0E0",
    fontSize: 13,
    fontWeight: "600",
  },
});
