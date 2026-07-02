<script setup lang="ts">
import {
  StatsChartOutline,
  PeopleOutline,
  CheckmarkCircleOutline,
  SettingsOutline,
  LogOutOutline,
  MenuOutline,
} from '@vicons/ionicons5'
import { useAdminStore } from '@/stores/admin'
import { useAuthStore } from '@/stores/auth'
import { useRouter, useRoute } from 'vue-router'
import type { MenuOption } from 'naive-ui'
import { h, type Component } from 'vue'
import { NIcon } from 'naive-ui'

const adminStore = useAdminStore()
const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

function renderIcon(icon: Component) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions: MenuOption[] = [
  { label: '数据看板', key: 'Dashboard', icon: renderIcon(StatsChartOutline) },
  { label: '学员管理', key: 'Users', icon: renderIcon(PeopleOutline) },
  { label: '审批管理', key: 'Approval', icon: renderIcon(CheckmarkCircleOutline) },
  { label: '系统设置', key: 'Settings', icon: renderIcon(SettingsOutline) },
]

function handleMenuClick(key: string) {
  router.push({ name: key })
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <NLayout style="height: 100vh">
    <!-- 顶部导航 -->
    <NLayoutHeader bordered style="height: 56px; padding: 0 24px; display: flex; align-items: center; justify-content: space-between">
      <div style="display: flex; align-items: center; gap: 12px">
        <NButton text @click="adminStore.toggleCollapsed">
          <NIcon size="20"><MenuOutline /></NIcon>
        </NButton>
        <span style="font-size: 15px; font-weight: 600; letter-spacing: -.02em; color: #111827; white-space: nowrap">
          CNC 培训管理后台
        </span>
      </div>
      <NDropdown
        trigger="click"
        :options="[
          { label: '退出登录', key: 'logout', icon: renderIcon(LogOutOutline) },
        ]"
        @select="handleLogout"
      >
        <div style="display: flex; align-items: center; gap: 8px; cursor: pointer">
          <div style="width: 28px; height: 28px; border-radius: 50%; background: #EEF2FF; color: #4F46E5; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600">
            {{ (authStore.user?.username || 'A').charAt(0).toUpperCase() }}
          </div>
          <span style="font-size: 13px; color: #4B5563">{{ authStore.user?.username || '管理员' }}</span>
        </div>
      </NDropdown>
    </NLayoutHeader>

    <NLayout style="height: calc(100vh - 56px)" has-sider>
      <!-- 侧边栏 -->
      <NLayoutSider
        bordered
        collapse-mode="width"
        :collapsed="adminStore.collapsed"
        :collapsed-width="64"
        :width="220"
      >
        <NMenu
          :collapsed="adminStore.collapsed"
          :collapsed-width="64"
          :options="menuOptions"
          :value="(route.name as string)"
          @update:value="handleMenuClick"
        />
      </NLayoutSider>

      <!-- 内容区 -->
      <NLayoutContent content-style="padding: 24px; overflow: auto; background: #FAFAFA">
        <RouterView />
      </NLayoutContent>
    </NLayout>
  </NLayout>
</template>
