<template>
  <div class="auth-page">
    <!-- 背景装饰 -->
    <div class="auth-bg">
      <div class="auth-bg__circle auth-bg__circle--1"></div>
      <div class="auth-bg__circle auth-bg__circle--2"></div>
      <div class="auth-bg__circle auth-bg__circle--3"></div>
    </div>

    <!-- 登录卡片 -->
    <div class="auth-container">
      <!-- 品牌标识 -->
      <div class="auth-brand">
        <span class="auth-brand__dot"></span>
        <span class="auth-brand__text">领域知识个性化生成系统</span>
      </div>

      <!-- 登录表单卡片 -->
      <div class="auth-card">
        <div class="auth-card__header">
          <h1 class="auth-card__title">欢迎回来</h1>
          <p class="auth-card__subtitle">登录您的账号以继续学习</p>
        </div>

        <form class="auth-form" @submit.prevent="handleLogin">
          <div class="auth-field">
            <label class="auth-field__label" for="username">用户名</label>
            <div class="auth-input-wrapper">
              <svg class="auth-input__icon" viewBox="0 0 20 20" fill="currentColor">
                <path d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" />
              </svg>
              <input
                id="username"
                v-model="formState.username"
                type="text"
                class="auth-input"
                placeholder="请输入用户名"
                autocomplete="username"
              />
            </div>
          </div>

          <div class="auth-field">
            <label class="auth-field__label" for="password">密码</label>
            <div class="auth-input-wrapper">
              <svg class="auth-input__icon" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd" />
              </svg>
              <input
                id="password"
                v-model="formState.password"
                type="password"
                class="auth-input"
                placeholder="请输入密码"
                autocomplete="current-password"
              />
            </div>
          </div>

          <button
            type="submit"
            class="auth-btn auth-btn--primary"
            :disabled="loading"
          >
            <svg v-if="loading" class="auth-btn__spinner" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-dasharray="31.416" stroke-dashoffset="10" />
            </svg>
            <span v-else>登录</span>
          </button>
        </form>

        <div class="auth-card__footer">
          <p class="auth-card__footer-text">
            还没有账号？
            <NuxtLink to="/register" class="auth-link">立即注册</NuxtLink>
          </p>
        </div>
      </div>

      <!-- 底部信息 -->
      <div class="auth-footer">
        <p class="auth-footer__text">© 2026 领域知识个性化生成与多智能体协同决策系统</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 禁用默认布局（不显示导航栏）
definePageMeta({
  layout: false,
})

const router = useRouter()
const api = useApi()
const toast = useToast()
const { setToken, setUser } = useAuth()

const loading = ref(false)
const formState = reactive({
  username: '',
  password: '',
})

const handleLogin = async () => {
  if (!formState.username || !formState.password) {
    toast.add({ title: '请填写用户名和密码', color: 'orange' })
    return
  }

  loading.value = true
  try {
    const result = await api.login({
      username: formState.username,
      password: formState.password,
    })

    setToken(result.access_token)
    setUser({ id: result.user_id, username: result.username })

    toast.add({ title: '登录成功', color: 'green' })
    router.push('/profile')
  } catch (err: any) {
    toast.add({ title: '登录失败', description: err.message, color: 'red' })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* ========== 页面布局 ========== */
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
  position: relative;
  overflow: hidden;
  padding: 20px;
}

/* ========== 背景装饰 ========== */
.auth-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.auth-bg__circle {
  position: absolute;
  border-radius: 50%;
  background: var(--accent-soft);
  opacity: 0.5;
}

.auth-bg__circle--1 {
  width: 600px;
  height: 600px;
  top: -200px;
  right: -150px;
  animation: float 20s ease-in-out infinite;
}

.auth-bg__circle--2 {
  width: 400px;
  height: 400px;
  bottom: -100px;
  left: -100px;
  animation: float 15s ease-in-out infinite reverse;
}

.auth-bg__circle--3 {
  width: 200px;
  height: 200px;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation: float 25s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  25% { transform: translate(20px, -20px); }
  50% { transform: translate(-10px, 20px); }
  75% { transform: translate(-20px, -10px); }
}

/* ========== 容器 ========== */
.auth-container {
  width: 100%;
  max-width: 420px;
  position: relative;
  z-index: 1;
}

/* ========== 品牌标识 ========== */
.auth-brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 32px;
}

.auth-brand__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
}

.auth-brand__text {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
  letter-spacing: -.02em;
}

/* ========== 登录卡片 ========== */
.auth-card {
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 40px 32px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.04);
}

.auth-card__header {
  text-align: center;
  margin-bottom: 32px;
}

.auth-card__title {
  font-size: 24px;
  font-weight: 600;
  color: var(--text);
  letter-spacing: -.03em;
  margin-bottom: 8px;
}

.auth-card__subtitle {
  font-size: 14px;
  color: var(--text-2);
}

/* ========== 表单 ========== */
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.auth-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.auth-field__label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-2);
}

.auth-input-wrapper {
  position: relative;
}

.auth-input__icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 18px;
  height: 18px;
  color: var(--text-3);
  pointer-events: none;
}

.auth-input {
  width: 100%;
  height: 44px;
  padding: 0 14px 0 40px;
  font-family: var(--font);
  font-size: 14px;
  color: var(--text);
  background: var(--bg);
  border: 1px solid var(--line-2);
  border-radius: var(--radius-sm);
  transition: all 0.15s ease;
  outline: none;
}

.auth-input::placeholder {
  color: var(--text-3);
}

.auth-input:hover {
  border-color: var(--text-3);
}

.auth-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

/* ========== 按钮 ========== */
.auth-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  height: 44px;
  font-family: var(--font);
  font-size: 14px;
  font-weight: 500;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.15s ease;
  margin-top: 8px;
}

.auth-btn--primary {
  background: var(--accent);
  color: #fff;
}

.auth-btn--primary:hover:not(:disabled) {
  background: #4338CA;
}

.auth-btn--primary:active:not(:disabled) {
  background: #3730A3;
  transform: translateY(1px);
}

.auth-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.auth-btn__spinner {
  width: 20px;
  height: 20px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ========== 底部链接 ========== */
.auth-card__footer {
  margin-top: 24px;
  text-align: center;
}

.auth-card__footer-text {
  font-size: 13px;
  color: var(--text-2);
}

.auth-link {
  color: var(--accent);
  font-weight: 500;
  text-decoration: none;
  transition: color 0.15s ease;
}

.auth-link:hover {
  color: #4338CA;
}

/* ========== 页面底部 ========== */
.auth-footer {
  margin-top: 32px;
  text-align: center;
}

.auth-footer__text {
  font-size: 12px;
  color: var(--text-3);
}

/* ========== 响应式 ========== */
@media (max-width: 480px) {
  .auth-card {
    padding: 32px 24px;
  }

  .auth-card__title {
    font-size: 20px;
  }
}
</style>
