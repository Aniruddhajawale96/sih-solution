import { View, Text, StyleSheet, TouchableOpacity, Alert } from "react-native";
import { useState } from "react";
import { Link } from "expo-router";
import { useSignIn } from "@clerk/clerk-expo";
import { AuthInput } from "@/components/auth/AuthInput";

export default function LoginScreen() {
  const { signIn, setActive, isLoaded } = useSignIn();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const onLogin = async () => {
    if (!isLoaded) return;
    setLoading(true);
    try {
      const result = await signIn.create({
        identifier: email,
        password,
      });
      if (result.status === "complete") {
        await setActive({ session: result.createdSessionId });
      } else {
        Alert.alert("Login incomplete", JSON.stringify(result));
      }
    } catch (err: any) {
      Alert.alert("Login failed", err.errors?.[0]?.message || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.logo}>KRISHI-NETRA</Text>
      <View style={styles.card}>
        <AuthInput
          placeholder="Email address"
          autoCapitalize="none"
          keyboardType="email-address"
          value={email}
          onChangeText={setEmail}
        />
        <AuthInput
          placeholder="Password"
          secureTextEntry
          value={password}
          onChangeText={setPassword}
        />
        <TouchableOpacity
          style={[styles.loginButton, loading && { opacity: 0.7 }]}
          onPress={onLogin}
          disabled={loading}
        >
          <Text style={styles.loginText}>
            {loading ? "Logging in..." : "Log in"}
          </Text>
        </TouchableOpacity>
        <View style={styles.divider} />
        <Link href="/(auth)/signup" asChild>
          <TouchableOpacity style={styles.createButton}>
            <Text style={styles.createText}>Create new account</Text>
          </TouchableOpacity>
        </Link>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f0f2f5", alignItems: "center", justifyContent: "center", paddingHorizontal: 20 },
  logo: { fontSize: 48, fontWeight: "bold", color: "#1877f2", marginBottom: 30 },
  card: { width: "100%", backgroundColor: "#fff", borderRadius: 10, padding: 16, elevation: 5 },
  loginButton: { backgroundColor: "#1877f2", paddingVertical: 12, borderRadius: 6, alignItems: "center", marginTop: 10 },
  loginText: { color: "#fff", fontSize: 16, fontWeight: "bold" },
  divider: { height: 1, backgroundColor: "#ddd", marginVertical: 16 },
  createButton: { backgroundColor: "#42b72a", paddingVertical: 12, borderRadius: 6, alignItems: "center" },
  createText: { color: "#fff", fontSize: 16, fontWeight: "bold" },
});
