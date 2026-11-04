import { Stack } from "expo-router";

export default function RootLayout() {
  return (
    <Stack>
      <Stack.Screen
        name="index"
        key={"home"}
        options={{ title: "Home", headerShown: false }}
      />
      <Stack.Screen
        name="test/index"
        key={"test"}
        options={{ title: "Test weather api", headerShown: true }}
      />
      <Stack.Screen
        name="farmPlanning/farmMap3D/index"
        key={"farm_planning"}
        options={{
          headerShown: true,
          headerShadowVisible: false,
          headerTransparent: true,
          headerTitle: "",
          headerBackTitle: "",
          headerTintColor: "#000", // chevron color
          headerBackButtonDisplayMode: "generic",
          headerStyle: {
            backgroundColor: "transparent",
          },
        }}
      />
      <Stack.Screen
        name="farmPlanning/farmMap/index"
        key={"farm_planning"}
        options={{
          headerShown: true,
          headerShadowVisible: false,
          headerTransparent: true,
          headerTitle: "",
          headerBackTitle: "",
          headerTintColor: "#000", // chevron color
          headerBackButtonDisplayMode: "generic",
          headerStyle: {
            backgroundColor: "transparent",
          },
        }}
      />
      <Stack.Screen
        name="farmPlanning/DetailScreen"
        key={"detailscreen"}
        options={{
          headerShown: true,
          headerShadowVisible: false,
          headerTransparent: true,
          headerTitle: "",
          headerBackTitle: "",
          headerTintColor: "#000", // chevron color
          headerBackButtonDisplayMode: "generic",
          headerStyle: {
            backgroundColor: "transparent",
          },
        }}
      />
    </Stack>
  );
}
