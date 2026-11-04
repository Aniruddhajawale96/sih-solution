import { StyleSheet } from "react-native";

const SIZES = {
  // Base spacing
  BASE: 8,

  // Spacing
  spacing: {
    SPACING_4: 4,
    SPACING_8: 8,
    SPACING_12: 12,
    SPACING_16: 16,
    SPACING_20: 20,
    SPACING_24: 24,
    SPACING_28: 28,
    SPACING_32: 32,
    SPACING_36: 36,
    SPACING_40: 40,
    SPACING_44: 44,
    SPACING_48: 48,
    SPACING_64: 64,
  },

  // icon
  icon: {
    XS: 12,
    SM: 16,
    MD: 20,
    LG: 24,
    XL: 32,
    XXL: 40,
  },

  // Component sizes
  component: {
    BUTTON_HEIGHT: 48,
    INPUT_HEIGHT: 44,
    ICON_SIZE: 24,
    ICON_LARGE: 32,
    CARD_MIN_HEIGHT: 120,
    CARD_MAX_WIDTH: 400,
  },

  // Radius
  radius: {
    XS: 4,
    SM: 8,
    MD: 12,
    LG: 16,
    XL: 24,
    FULL: 9999,

    // legacy
    RADIUS_SMALL: 4,
    RADIUS: 8,
    RADIUS_LARGE: 16,
    RADIUS_XL: 24,
  },

  // Typography sizes use FONT_SIZES instead
  text: {
    TEXT_SMALL: 12,
    text: 14,
    TEXT_MEDIUM: 16,
    TEXT_LARGE: 20,
    TEXT_XL: 24,
    HEADING: 32,
  },

  // Layout widths
  layour_width: {
    SCREEN_WIDTH_PERCENT: "100%",
    CARD_WIDTH_PERCENT: "90%",
    CENTERED_WIDTH_PERCENT: "80%",
  },

  // Aspect ratios
  aspect_ratio: {
    ASPECT_RATIO_SQUARE: 1,
    ASPECT_RATIO_WIDE: 16 / 9,
    ASPECT_RATIO_PORTRAIT: 3 / 4,
  },

  image_sizes: {
    // Common Aspect Ratios
    ASPECT_RATIO_SQUARE: 1,
    ASPECT_RATIO_WIDE: 16 / 9,
    ASPECT_RATIO_PORTRAIT: 3 / 4,

    // Common Image Dimensions (in dp)
    // 👤 Avatars / Icons
    AVATAR_XS: 24,
    AVATAR_SM: 32,
    AVATAR_MD: 48,
    AVATAR_LG: 64,
    AVATAR_XL: 80,

    // 🖼️ Thumbnails / Small Images
    THUMBNAIL_SM: 60,
    THUMBNAIL_MD: 80,
    THUMBNAIL_LG: 100,

    // 🃏 Cards / Banners
    CARD_IMAGE_WIDTH: "100%",
    CARD_IMAGE_HEIGHT: 180,

    BANNER_IMAGE_HEIGHT: 240,
    HERO_IMAGE_HEIGHT: 300,

    // 🌇 Full Width Image
    FULL_WIDTH: "100%",
    FULL_HEIGHT: "100%",

    // Radius
    IMAGE_RADIUS_SM: 8,
    IMAGE_RADIUS_LG: 16,
  },

  // separator
  separator_height: {
    HAIRLINE: StyleSheet.hairlineWidth, // Ultra-thin line (0.5 - 1 pixel)
    THIN: 1,
    MEDIUM: 2,
    THICK: 4,
    XL: 8,
  },
};

export default SIZES;
