import { Stack } from "expo-router";
import "@/lib/i18n";
import "@/polyfills/domParser";

import { SplashScreenController } from "@/components/shared/splashScreen/SplashScreenController";
import { useAuthContext } from "@/hooks/use-auth-context";
import AuthProvider from "@/providers/auth-provider";
import { StatusBar } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";

function RootNavigator() {
  const { isLoggedIn } = useAuthContext();
  return (
    <Stack>
      <Stack.Protected guard={isLoggedIn}>
        <Stack.Screen
          name="(main)"
          options={{ title: "home", headerShown: false }}
        />
      </Stack.Protected>
      <Stack.Protected guard={!isLoggedIn}>
        <Stack.Screen
          name="(auth)/login"
          options={{
            headerShown: false,
            headerShadowVisible: false,
            title: "Login",
          }}
        />
        <Stack.Screen
          name="(auth)/signup"
          options={{
            headerShown: false,
            headerShadowVisible: false,
            title: "Signup",
          }}
        />
      </Stack.Protected>

      <Stack.Screen
        name="map/index"
        key={"map"}
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
        name="modal"
        options={{ presentation: "modal", title: "Modal" }}
      />
    </Stack>
  );
}
export default function RootLayout() {
  return (
    <AuthProvider>
      <SplashScreenController />
      <GestureHandlerRootView style={{ flex: 1 }}>
        <RootNavigator />
      </GestureHandlerRootView>
      <StatusBar barStyle="dark-content" />
    </AuthProvider>
  );
}
