<template>
  <div class="container mx-auto px-4 py-16">
    <div class="max-w-md mx-auto">
      <UCard>
        <template #header>
          <h1 class="text-2xl font-bold text-center">登录</h1>
        </template>

        <UForm :state="formState" class="space-y-4" @submit="handleLogin">
          <UFormGroup label="用户名" name="username">
            <UInput
              v-model="formState.username"
              placeholder="请输入用户名"
              icon="i-heroicons-user"
            />
          </UFormGroup>

          <UFormGroup label="密码" name="password">
            <UInput
              v-model="formState.password"
              type="password"
              placeholder="请输入密码"
              icon="i-heroicons-lock-closed"
            />
          </UFormGroup>

          <UButton type="submit" block :loading="loading">
            登录
          </UButton>
        </UForm>

        <template #footer>
          <p class="text-center text-sm text-gray-500">
            还没有账号？
            <NuxtLink to="/register" class="text-primary font-medium">立即注册</NuxtLink>
          </p>
        </template>
      </UCard>
    </div>
  </div>
</template>

<script setup lang="ts">
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
