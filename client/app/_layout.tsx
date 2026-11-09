import { Stack, useRouter, useSegments } from "expo-router";
import "@/lib/i18n";
import "@/polyfills/domParser";

import { SplashScreenController } from "@/components/shared/splashScreen/SplashScreenController";
import AuthProvider from "@/providers/auth-provider";
import { useAuth } from "@clerk/clerk-expo";
import { useEffect } from "react";
import { StatusBar } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";

function RootNavigator() {
  const { isLoaded, isSignedIn } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (!isLoaded) return;
    const inAuthGroup = segments[0] === "(auth)";
    if (!isSignedIn && !inAuthGroup) {
      router.replace("/(auth)/login");
    } else if (isSignedIn && inAuthGroup) {
      router.replace("/(main)/(home)");
    }
  }, [isLoaded, isSignedIn, segments]);

  return (
    <Stack>
      <Stack.Screen name="(main)" options={{ headerShown: false }} />
      <Stack.Screen name="(auth)/login" options={{ headerShown: false, title: "Login" }} />
      <Stack.Screen name="(auth)/signup" options={{ headerShown: false, title: "Signup" }} />
      <Stack.Screen
        name="map/index"
        options={{
          headerShown: true,
          headerShadowVisible: false,
          headerTransparent: true,
          headerTitle: "",
          headerBackTitle: "",
          headerTintColor: "#000",
          headerBackButtonDisplayMode: "generic",
          headerStyle: { backgroundColor: "transparent" },
        }}
      />
      <Stack.Screen name="modal" options={{ presentation: "modal", title: "Modal" }} />
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
