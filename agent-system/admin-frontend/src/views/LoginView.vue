<script setup lang="ts">
import type { FormInst, FormRules } from 'naive-ui'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'
import { PersonOutline, LockClosedOutline } from '@vicons/ionicons5'

const router = useRouter()
const authStore = useAuthStore()
const message = useMessage()

const formRef = ref<FormInst | null>(null)
const loading = ref(false)

const formValue = reactive({
  username: '',
  password: '',
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const result = await authApi.login(formValue.username, formValue.password)

    if (result.role !== 'admin') {
      message.error('无管理员权限，请联系管理员')
      return
    }

    authStore.setToken(result.access_token)
    authStore.setUser({
      id: result.user_id,
      username: result.username,
      email: '',
      role: result.role as 'admin',
    })

    message.success('登录成功')
    router.push('/')
  } catch (err: any) {
    message.error(err.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <!-- 背景装饰 -->
    <div class="login-bg">
      <div class="login-bg-circle login-bg-circle--1" />
      <div class="login-bg-circle login-bg-circle--2" />
      <div class="login-bg-circle login-bg-circle--3" />
    </div>

    <div class="login-wrapper">
      <!-- 品牌标识 -->
      <div class="login-brand">
        <span class="login-brand-dot" />
        <span class="login-brand-text">CNC 培训管理后台</span>
      </div>

      <!-- 登录卡片 -->
      <div class="login-card">
        <div class="login-card-header">
          <h1 class="login-card-title">管理员登录</h1>
          <p class="login-card-subtitle">请使用管理员账号登录系统</p>
        </div>

        <NForm ref="formRef" :model="formValue" :rules="rules" @submit.prevent="handleLogin">
          <NFormItem path="username">
            <NInput
              v-model:value="formValue.username"
              placeholder="请输入用户名"
              size="large"
              :input-props="{ autocomplete: 'username' }"
            >
              <template #prefix>
                <NIcon :component="PersonOutline" />
              </template>
            </NInput>
          </NFormItem>

          <NFormItem path="password">
            <NInput
              v-model:value="formValue.password"
              type="password"
              placeholder="请输入密码"
              size="large"
              :input-props="{ autocomplete: 'current-password' }"
              @keyup.enter="handleLogin"
            >
              <template #prefix>
                <NIcon :component="LockClosedOutline" />
              </template>
            </NInput>
          </NFormItem>

          <NButton
            type="primary"
            size="large"
            :loading="loading"
            block
            @click="handleLogin"
          >
            登 录
          </NButton>
        </NForm>

        <div class="login-card-footer">
          <span>© 2026 领域知识个性化生成与多智能体协同决策系统</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--n-color, #fff);
  position: relative;
  overflow: hidden;
  padding: 20px;
}

/* 背景装饰 */
.login-bg { position: absolute; inset: 0; pointer-events: none; }
.login-bg-circle {
  position: absolute;
  border-radius: 50%;
  background: #EEF2FF;
  opacity: 0.5;
}
.login-bg-circle--1 {
  width: 600px; height: 600px;
  top: -200px; right: -150px;
  animation: float 20s ease-in-out infinite;
}
.login-bg-circle--2 {
  width: 400px; height: 400px;
  bottom: -100px; left: -100px;
  animation: float 15s ease-in-out infinite reverse;
}
.login-bg-circle--3 {
  width: 200px; height: 200px;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  animation: float 25s ease-in-out infinite;
}
@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  25% { transform: translate(20px, -20px); }
  50% { transform: translate(-10px, 20px); }
  75% { transform: translate(-20px, -10px); }
}

/* 容器 */
.login-wrapper {
  width: 100%;
  max-width: 420px;
  position: relative;
  z-index: 1;
}

/* 品牌 */
.login-brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 32px;
}
.login-brand-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #4F46E5;
}
.login-brand-text {
  font-size: 15px; font-weight: 600;
  color: #111827;
  letter-spacing: -.02em;
}

/* 卡片 */
.login-card {
  background: #fff;
  border: 1px solid #ECECEF;
  border-radius: 10px;
  padding: 40px 32px;
  box-shadow: 0 4px 24px rgba(0,0,0,.04);
}
.login-card-header {
  text-align: center;
  margin-bottom: 32px;
}
.login-card-title {
  font-size: 24px; font-weight: 600;
  color: #111827;
  letter-spacing: -.03em;
  margin-bottom: 8px;
}
.login-card-subtitle {
  font-size: 14px; color: #9CA3AF;
}
.login-card-footer {
  margin-top: 24px;
  text-align: center;
  font-size: 12px;
  color: #9CA3AF;
}
</style>
