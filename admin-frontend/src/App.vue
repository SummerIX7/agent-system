<script setup lang="ts">
import { NConfigProvider, zhCN, dateZhCN, NMessageProvider, NDialogProvider } from 'naive-ui'
import type { GlobalThemeOverrides } from 'naive-ui'

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#4F46E5',
    primaryColorHover: '#4338CA',
    primaryColorPressed: '#3730A3',
    primaryColorSuppl: '#4F46E5',
    successColor: '#059669',
    warningColor: '#D97706',
    errorColor: '#DC2626',
    textColorBase: '#111827',
    textColor1: '#111827',
    textColor2: '#4B5563',
    textColor3: '#9CA3AF',
    borderColor: '#ECECEF',
    dividerColor: '#ECECEF',
    borderRadius: '6px',
    borderRadiusSmall: '4px',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif',
  },
  Layout: {
    siderBorderColor: '#ECECEF',
    headerBorderColor: '#ECECEF',
    footerBorderColor: '#ECECEF',
  },
  Menu: {
    itemTextColor: '#4B5563',
    itemTextColorHover: '#4F46E5',
    itemTextColorActive: '#4F46E5',
    itemColorActive: '#EEF2FF',
    itemIconColor: '#9CA3AF',
    itemIconColorHover: '#4F46E5',
    itemIconColorActive: '#4F46E5',
  },
  Card: {
    borderRadius: '10px',
    borderColor: '#ECECEF',
  },
  Table: {
    borderColor: '#ECECEF',
    thColor: '#FAFAFA',
    tdColor: '#FFFFFF',
    thTextColor: '#4B5563',
    tdTextColor: '#111827',
  },
  Button: {
    borderRadiusSmall: '6px',
    borderRadiusMedium: '6px',
  },
}
</script>

<template>
  <NConfigProvider :locale="zhCN" :date-locale="dateZhCN" :theme-overrides="themeOverrides">
    <NMessageProvider>
      <!-- NDialogProvider 必须存在：SettingsView 使用 useDialog() 做删除确认，
           naive-ui 在缺少 Provider 时会直接 throwError，导致删除按钮点了没反应。 -->
      <NDialogProvider>
        <RouterView />
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>
