<script setup lang="ts">
import { useAdminStore } from '@/stores/admin'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const adminStore = useAdminStore()
const authStore = useAuthStore()
const router = useRouter()

const menuOptions = [
  { label: '数据看板', key: 'Dashboard', icon: 'stats-chart' },
  { label: '学员管理', key: 'Users', icon: 'people' },
  { label: '审批管理', key: 'Approval', icon: 'checkmark-circle' },
  { label: '系统设置', key: 'Settings', icon: 'settings' },
]

function handleMenuClick(key: string) {
  router.push({ name: key })
}
</script>

<template>
  <NLayout style="height: 100vh">
    <NLayoutHeader bordered style="height: 56px; padding: 0 24px; display: flex; align-items: center; justify-content: space-between">
      <span style="font-size: 18px; font-weight: 600">CNC 培训管理后台</span>
      <NDropdown>
        <NButton text>{{ authStore.user?.username ?? '管理员' }}</NButton>
      </NDropdown>
    </NLayoutHeader>
    <NLayout style="height: calc(100vh - 56px)" has-sider>
      <NLayoutSider bordered collapse-mode="width" :collapsed="adminStore.collapsed" :collapsed-width="64" :width="220">
        <NMenu
          :collapsed="adminStore.collapsed"
          :collapsed-width="64"
          :options="menuOptions"
          :value="router.currentRoute.value.name"
          @update:value="handleMenuClick"
        />
      </NLayoutSider>
      <NLayoutContent content-style="padding: 24px; overflow: auto">
        <RouterView />
      </NLayoutContent>
    </NLayout>
  </NLayout>
</template>
