import type { ThemeConfig } from "antd";

const luxuryTheme: ThemeConfig = {
  token: {
    colorPrimary: "#B8860B",
    colorInfo: "#B8860B",
    colorSuccess: "#5B8C5A",
    colorWarning: "#C48B2C",
    colorError: "#A63D40",
    colorBgContainer: "#FFFFFF",
    colorBgLayout: "#F7F5F2",
    colorBgElevated: "#FFFFFF",
    colorText: "#1A1A1A",
    colorTextSecondary: "#6B6B6B",
    colorTextTertiary: "#999999",
    colorTextQuaternary: "#BFBFBF",
    colorBorder: "#E8E4DF",
    colorBorderSecondary: "#F0ECE7",
    colorFill: "#F7F5F2",
    colorFillSecondary: "#FAFAF8",
    borderRadius: 10,
    fontFamily:
      "'Cormorant Garamond', 'Noto Serif SC', 'Songti SC', 'Georgia', 'Times New Roman', serif",
    fontSize: 14,
    fontSizeHeading1: 36,
    fontSizeHeading2: 28,
    fontSizeHeading3: 22,
    fontSizeHeading4: 18,
    lineHeight: 1.7,
    controlHeight: 40,
    controlHeightLG: 48,
    controlHeightSM: 32,
    boxShadow:
      "0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02)",
    boxShadowSecondary:
      "0 4px 12px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.03)",
  },
  components: {
    Button: {
      borderRadius: 8,
      controlHeight: 40,
      fontWeight: 500,
      defaultShadow: "none",
      primaryShadow: "0 2px 8px rgba(184,134,11,0.25)",
    },
    Card: {
      borderRadiusLG: 16,
      paddingLG: 28,
    },
    Table: {
      borderRadiusLG: 12,
      headerBg: "#FAFAF8",
      headerColor: "#6B6B6B",
      rowHoverBg: "#FBF9F6",
      fontSize: 14,
      cellPaddingInline: 20,
      cellPaddingBlock: 16,
    },
    Input: {
      borderRadius: 8,
      activeShadow: "0 0 0 2px rgba(184,134,11,0.1)",
    },
    Select: {
      borderRadius: 8,
    },
    Menu: {
      itemBorderRadius: 8,
      itemMarginInline: 8,
      itemHeight: 44,
      iconSize: 16,
      collapsedIconSize: 18,
    },
    Modal: {
      borderRadiusLG: 16,
    },
    Steps: {
      colorPrimary: "#B8860B",
    },
    Tag: {
      borderRadiusSM: 6,
    },
    Statistic: {
      fontSize: 36,
      titleFontSize: 13,
    },
    Upload: {
      borderRadius: 12,
    },
    Message: {
      borderRadiusLG: 10,
    },
  },
};

export default luxuryTheme;
