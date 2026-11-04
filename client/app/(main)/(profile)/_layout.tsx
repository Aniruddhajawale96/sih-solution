import { Stack } from "expo-router";

export default function RootLayout() {
  return (
    <Stack>
      <Stack.Screen
        name="index"
        key={"profile"}
        options={{ title: "Profile", headerShown: false }}
      />
    </Stack>
  );
}
