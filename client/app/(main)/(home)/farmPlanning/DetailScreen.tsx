import {
  StyleSheet,
  Text,
  View,
  TextInput,
  Pressable,
  Image,
} from "react-native";
import React, { useState } from "react";
import useAppStore from "@/store";
import { router } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { SoilType } from "@/types/farm";
import { ScrollView } from "react-native-gesture-handler";

const SOIL_TYPES: {
  key: SoilType;
  label: string;
  image: any;
}[] = [
  {
    key: "clay",
    label: "Clay Soil",
    image:
      "https://img.freepik.com/free-photo/close-up-mixture-clay-powder_23-2148761860.jpg?semt=ais_hybrid&w=740&q=80",
  },
  {
    key: "sandy",
    label: "Sandy Soil",
    image:
      "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTZmIW1U5ED-_BpYBDgH0LxFrgdgTF0AiVleQ&s",
  },
  {
    key: "loamy",
    label: "Loamy Soil",
    image:
      "https://media.istockphoto.com/id/1407833126/photo/the-mans-hand-touches-the-loamy-soil-with-proper-technology-for-cultivating-the-soil.jpg?s=612x612&w=0&k=20&c=FLED92hqqdMHh-43_A_jATVhlFUgWJVTuQ7kRuBldOI=",
  },
  {
    key: "red soil",
    label: "Red Soil",
    image:
      "https://img.freepik.com/premium-photo/natural-red-soil-background_302321-7522.jpg?semt=ais_user_personalization&w=740&q=80",
  },
  {
    key: "alluvial",
    label: "Alluvial Soil",
    image:
      "https://5.imimg.com/data5/SELLER/Default/2022/9/NX/HC/LL/46402544/alluvium-soil.jpg",
  },
  {
    key: "black soil",
    label: "Black Soil",
    image:
      "https://img.freepik.com/premium-photo/close-up-black-soil-background_105428-914.jpg?semt=ais_hybrid&w=740&q=80",
  },
];

const FillDetails = () => {
  const [farmRegNo, setFarmRegNo] = useState("");
  const [budgetLocal, setBudgetLocal] = useState<number>(0);
  const {
    setSoilType: soilTypeset,
    setRegistrationNumber,
    soilType: soiltype,
    setBudget,
  } = useAppStore();

  const [soilType, setSoilType] = useState<SoilType>(soiltype);
  const isValid =
    farmRegNo.trim().length > 3 && soilType !== null && budgetLocal > 0;

  const handleContinue = () => {
    // later you can save this in zustand
    // useAppStore.getState().setFarmDetails({ farmRegNo, soilType });
    console.log("Pressed");
    soilTypeset(soilType);
    setRegistrationNumber(farmRegNo);
    setBudget(budgetLocal);
    router.navigate("/(main)/(home)/farmPlanning/farmMap");
  };

  const handleBudgetChange = (text: string) => {
    // Remove any non-numeric characters
    const numericText = text.replace(/[^0-9]/g, "");

    if (numericText === "") {
      setBudgetLocal(0);
    } else {
      const parsedValue = parseInt(numericText, 10);
      setBudgetLocal(isNaN(parsedValue) ? 0 : parsedValue);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.title}>Farm Details</Text>

      {/* Farm Registration Number */}
      <View style={styles.section}>
        <Text style={styles.label}>Farm Registration Number</Text>
        <TextInput
          placeholder="Enter registration number"
          value={farmRegNo}
          onChangeText={setFarmRegNo}
          style={styles.input}
        />
      </View>

      {/* Soil Type */}
      <View style={styles.section}>
        <Text style={styles.label}>Soil Type</Text>

        <ScrollView
          horizontal
          contentContainerStyle={[styles.soilRow, { gap: 8 }]}
        >
          {SOIL_TYPES.map((soil) => {
            const selected = soilType === soil.key;

            return (
              <Pressable
                key={soil.key}
                onPress={() => setSoilType(soil.key)}
                style={[styles.soilCard, selected && styles.soilCardSelected]}
              >
                <Image source={{ uri: soil.image }} style={styles.soilImage} />
                <Text
                  style={[styles.soilText, selected && styles.soilTextSelected]}
                >
                  {soil.label}
                </Text>
              </Pressable>
            );
          })}
        </ScrollView>
      </View>
      <View style={styles.section}>
        <Text style={styles.label}>Budget</Text>
        <TextInput
          placeholder="Enter registration number"
          value={budgetLocal.toString()}
          onChangeText={handleBudgetChange}
          style={styles.input}
          keyboardType="number-pad"
        />
      </View>
      {/* Continue Button */}
      <Pressable
        disabled={!isValid}
        onPress={handleContinue}
        style={[styles.button, !isValid && styles.buttonDisabled]}
      >
        <Text style={styles.buttonText}>Continue</Text>
      </Pressable>
    </SafeAreaView>
  );
};

export default FillDetails;

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: "#fff",
    marginTop: 40,
  },
  title: {
    fontSize: 24,
    fontWeight: "600",
    marginBottom: 24,
  },
  section: {
    marginBottom: 24,
  },
  label: {
    fontSize: 14,
    marginBottom: 8,
    color: "#555",
  },
  input: {
    borderWidth: 1,
    borderColor: "#ddd",
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
  },
  soilRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingBottom: 15,
  },
  soilCard: {
    flex: 1,
    borderWidth: 1,
    borderColor: "#ddd",
    borderRadius: 12,
    alignItems: "center",
    padding: 12,
    marginHorizontal: 4,
    height: 150,
    width: 120,
  },
  soilCardSelected: {
    borderColor: "#2e7d32",
    backgroundColor: "#e8f5e9",
  },
  soilImage: {
    flex: 1,
    width: "100%",
    height: "100%",
    marginBottom: 8,
  },
  soilText: {
    fontSize: 13,
    color: "#444",
  },
  soilTextSelected: {
    color: "#2e7d32",
    fontWeight: "600",
  },
  button: {
    marginTop: "auto",
    backgroundColor: "#2e7d32",
    paddingVertical: 16,
    borderRadius: 14,
    alignItems: "center",
  },
  buttonDisabled: {
    backgroundColor: "#a5d6a7",
  },
  buttonText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
});
