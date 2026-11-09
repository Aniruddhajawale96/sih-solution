import { View, Text, StyleSheet, TouchableOpacity, ScrollView, Platform, Alert } from "react-native";
import { useState } from "react";
import { Link } from "expo-router";
import DateTimePicker from "@react-native-community/datetimepicker";
import { useSignUp } from "@clerk/clerk-expo";
import { AuthInput } from "@/components/auth/AuthInput";

export default function SignupScreen() {
  const { signUp, setActive, isLoaded } = useSignUp();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [pendingVerification, setPendingVerification] = useState(false);
  const [code, setCode] = useState("");

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [dob, setDob] = useState<Date | null>(null);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [mobile, setMobile] = useState("");
  const [address, setAddress] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [accountHolder, setAccountHolder] = useState("");
  const [accountNo, setAccountNo] = useState("");
  const [ifsc, setIfsc] = useState("");
  const [bankName, setBankName] = useState("");
  const [branchName, setBranchName] = useState("");

  const nextStep = () => setStep((s) => Math.min(s + 1, 2));
  const prevStep = () => setStep((s) => Math.max(s - 1, 1));

  const validateStep1 = () => {
    if (!firstName || !lastName || !dob || !mobile || !address || !email || !password) {
      Alert.alert("Please fill all required fields in Step 1");
      return false;
    }
    return true;
  };

  const validateStep2 = () => {
    if (!accountHolder || !accountNo || !ifsc || !bankName || !branchName) {
      Alert.alert("Please fill all required bank details");
      return false;
    }
    return true;
  };

  const submitAll = async () => {
    if (!isLoaded) return;
    if (!validateStep1() || !validateStep2()) return;
    setLoading(true);
    try {
      await signUp.create({
        emailAddress: email,
        password,
        firstName,
        lastName,
      });
      await signUp.prepareEmailAddressVerification({ strategy: "email_code" });
      setPendingVerification(true);
    } catch (err: any) {
      Alert.alert("Signup failed", err.errors?.[0]?.message || err.message);
    } finally {
      setLoading(false);
    }
  };

  const onVerify = async () => {
    if (!isLoaded) return;
    setLoading(true);
    try {
      const result = await signUp.attemptEmailAddressVerification({ code });
      if (result.status === "complete") {
        await setActive({ session: result.createdSessionId });
      } else {
        Alert.alert("Verification incomplete", JSON.stringify(result));
      }
    } catch (err: any) {
      Alert.alert("Verification failed", err.errors?.[0]?.message || err.message);
    } finally {
      setLoading(false);
    }
  };

  if (pendingVerification) {
    return (
      <View style={styles.container}>
        <Text style={styles.logo}>Verify Email</Text>
        <View style={styles.card}>
          <Text style={{ marginBottom: 12, color: "#555" }}>
            Enter the verification code sent to {email}
          </Text>
          <AuthInput
            placeholder="Verification code"
            keyboardType="number-pad"
            value={code}
            onChangeText={setCode}
          />
          <TouchableOpacity
            style={[styles.signupButton, loading && { opacity: 0.7 }]}
            onPress={onVerify}
            disabled={loading}
          >
            <Text style={styles.signupText}>{loading ? "Verifying..." : "Verify"}</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  const renderStep1 = () => (
    <>
      <AuthInput placeholder="First name" value={firstName} onChangeText={setFirstName} />
      <AuthInput placeholder="Last name" value={lastName} onChangeText={setLastName} />
      <TouchableOpacity style={styles.dateInput} onPress={() => setShowDatePicker(true)}>
        <Text style={{ color: dob ? "#000" : "#888" }}>
          {dob ? dob.toDateString() : "Select Date of Birth"}
        </Text>
      </TouchableOpacity>
      {showDatePicker && (
        <DateTimePicker
          value={dob || new Date()}
          mode="date"
          display={Platform.OS === "ios" ? "spinner" : "default"}
          maximumDate={new Date()}
          onChange={(event, selectedDate) => {
            setShowDatePicker(false);
            if (selectedDate) setDob(selectedDate);
          }}
        />
      )}
      <View style={{ height: 10 }} />
      <AuthInput placeholder="Mobile number" keyboardType="phone-pad" value={mobile} onChangeText={setMobile} />
      <AuthInput placeholder="Current address" value={address} onChangeText={setAddress} />
      <AuthInput placeholder="Email" value={email} onChangeText={setEmail} autoCapitalize="none" />
      <AuthInput placeholder="Password" secureTextEntry value={password} onChangeText={setPassword} />
    </>
  );

  const renderStep2 = () => (
    <>
      <AuthInput placeholder="Account holder name" value={accountHolder} onChangeText={setAccountHolder} />
      <AuthInput placeholder="Account number" keyboardType="number-pad" value={accountNo} onChangeText={setAccountNo} />
      <AuthInput placeholder="IFSC code" value={ifsc} onChangeText={setIfsc} />
      <AuthInput placeholder="Bank name" value={bankName} onChangeText={setBankName} />
      <AuthInput placeholder="Branch name" value={branchName} onChangeText={setBranchName} />
    </>
  );

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <Text style={styles.logo}>Sign-Up</Text>
        <Text style={styles.step}>Step {step} of 2</Text>
        <View style={styles.card}>
          {step === 1 && renderStep1()}
          {step === 2 && renderStep2()}
          {step < 2 ? (
            <TouchableOpacity style={styles.nextButton} onPress={() => { if (validateStep1()) nextStep(); }}>
              <Text style={styles.nextText}>Next</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity style={[styles.signupButton, loading && { opacity: 0.7 }]} onPress={submitAll} disabled={loading}>
              <Text style={styles.signupText}>{loading ? "Submitting..." : "Finish Signup"}</Text>
            </TouchableOpacity>
          )}
          {step > 1 && (
            <TouchableOpacity onPress={prevStep}>
              <Text style={styles.back}>Back</Text>
            </TouchableOpacity>
          )}
          <View style={styles.divider} />
          <Link href="/(auth)/login" asChild>
            <TouchableOpacity style={styles.loginButton}>
              <Text style={styles.loginText}>Already have an account?</Text>
            </TouchableOpacity>
          </Link>
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f0f2f5" },
  scroll: { alignItems: "center", justifyContent: "center", padding: 20, paddingBottom: 40 },
  logo: { fontSize: 48, fontWeight: "bold", color: "#1877f2", marginBottom: 10 },
  step: { fontSize: 16, marginBottom: 10, color: "#555" },
  card: { width: "100%", backgroundColor: "#fff", borderRadius: 10, padding: 16, elevation: 5 },
  nextButton: { backgroundColor: "#1877f2", padding: 12, borderRadius: 6, alignItems: "center", marginTop: 12 },
  nextText: { color: "#fff", fontWeight: "bold" },
  signupButton: { backgroundColor: "#42b72a", padding: 12, borderRadius: 6, alignItems: "center", marginTop: 12 },
  signupText: { color: "#fff", fontWeight: "bold" },
  back: { textAlign: "center", marginTop: 10, color: "#1877f2" },
  divider: { height: 1, backgroundColor: "#ddd", marginVertical: 16 },
  loginButton: { backgroundColor: "#1877f2", paddingVertical: 12, borderRadius: 6, alignItems: "center" },
  loginText: { color: "#fff", fontWeight: "bold" },
  dateInput: { borderWidth: 1, borderColor: "#ccc", borderRadius: 6, padding: 12 },
});
