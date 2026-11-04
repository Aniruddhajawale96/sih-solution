import { View, Text, StyleSheet, TouchableOpacity } from "react-native";
import { useState } from "react";
import { Link } from "expo-router";
import { supabase } from "@/lib/services/supabase";
import { AuthInput } from "@/components/auth/AuthInput";

export default function LoginScreen() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const onLogin = async () => {
    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (error) alert(error.message);
    setLoading(false);
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
  container: {
    flex: 1,
    backgroundColor: "#f0f2f5",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 20,
  },
  logo: {
    fontSize: 48,
    fontWeight: "bold",
    color: "#1877f2",
    marginBottom: 30,
  },
  card: {
    width: "100%",
    backgroundColor: "#fff",
    borderRadius: 10,
    padding: 16,
    shadowColor: "#000",
    shadowOpacity: 0.1,
    shadowRadius: 10,
    elevation: 5,
  },
  loginButton: {
    backgroundColor: "#1877f2",
    paddingVertical: 12,
    borderRadius: 6,
    alignItems: "center",
    marginTop: 10,
  },
  loginText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "bold",
  },
  forgot: {
    textAlign: "center",
    color: "#1877f2",
    marginTop: 12,
    fontSize: 14,
  },
  divider: {
    height: 1,
    backgroundColor: "#ddd",
    marginVertical: 16,
  },
  createButton: {
    backgroundColor: "#42b72a",
    paddingVertical: 12,
    borderRadius: 6,
    alignItems: "center",
  },
  createText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "bold",
  },
});
