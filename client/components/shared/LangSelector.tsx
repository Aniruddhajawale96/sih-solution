import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { useTranslation } from "react-i18next";
import PressableOpacity from "@/components/shared/PressableOpacity";
import SIZES from "@/constants/sizes";

type Language = {
  code: string;
  label: string;
};

const LANGUAGES: Language[] = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
];

export default function LanguageSelector() {
  const { i18n } = useTranslation();
  const currentLang = i18n.language;

  const changeLanguage = (lang: string) => {
    if (lang !== currentLang) {
      i18n.changeLanguage(lang);
    }
  };

  return (
    <View style={styles.container}>
      {LANGUAGES.map((lang) => {
        const isActive = currentLang === lang.code;

        return (
          <PressableOpacity
            key={lang.code}
            onPress={() => changeLanguage(lang.code)}
            style={[styles.option, isActive && styles.optionActive]}
          >
            <Text style={[styles.text, isActive && styles.textActive]}>
              {lang.label}
            </Text>
          </PressableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    gap: 12,
  },

  option: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: SIZES.radius.FULL,
    backgroundColor: "#F2F2F2",
  },

  optionActive: {
    backgroundColor: "#007AFF22",
  },

  text: {
    fontSize: 14,
    color: "#444",
    fontWeight: "500",
  },

  textActive: {
    color: "#007AFF",
    fontWeight: "600",
  },
});
