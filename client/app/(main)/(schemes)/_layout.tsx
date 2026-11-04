import { Stack } from "expo-router";

export default function RootLayout() {
  return (
    <Stack>
      <Stack.Screen
        name="index"
        key={"schemes"}
        options={{ title: "Schemes", headerShown: false }}
      />
      <Stack.Screen
        name="scheme-form"
        key={"scheme-form"}
        options={{ title: "Scheme Form", headerShown: true }}
      />
      <Stack.Screen
        name="scheme/apply"
        key={"apply"}
        options={{ title: "Apply for scheme", headerShown: true }}
      />
    </Stack>
  );
}
