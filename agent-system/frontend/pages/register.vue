<template>
  <div class="container mx-auto px-4 py-16">
    <div class="max-w-md mx-auto">
      <UCard>
        <template #header>
          <h1 class="text-2xl font-bold text-center">注册</h1>
        </template>

        <UForm :state="formState" class="space-y-4" @submit="handleRegister">
          <UFormGroup label="用户名" name="username">
            <UInput
              v-model="formState.username"
              placeholder="请输入用户名"
              icon="i-heroicons-user"
            />
          </UFormGroup>

          <UFormGroup label="邮箱" name="email">
            <UInput
              v-model="formState.email"
              type="email"
              placeholder="请输入邮箱（可选）"
              icon="i-heroicons-envelope"
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

          <UFormGroup label="确认密码" name="confirmPassword">
            <UInput
              v-model="formState.confirmPassword"
              type="password"
              placeholder="请再次输入密码"
              icon="i-heroicons-lock-closed"
            />
          </UFormGroup>

          <UButton type="submit" block :loading="loading">
            注册
          </UButton>
        </UForm>

        <template #footer>
          <p class="text-center text-sm text-gray-500">
            已有账号？
            <NuxtLink to="/login" class="text-primary font-medium">立即登录</NuxtLink>
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
  email: '',
  password: '',
  confirmPassword: '',
})

const handleRegister = async () => {
  if (!formState.username || !formState.password) {
    toast.add({ title: '请填写用户名和密码', color: 'orange' })
    return
  }

  if (formState.password !== formState.confirmPassword) {
    toast.add({ title: '两次密码不一致', color: 'orange' })
    return
  }

  if (formState.password.length < 6) {
    toast.add({ title: '密码至少 6 位', color: 'orange' })
    return
  }

  loading.value = true
  try {
    const result = await api.register({
      username: formState.username,
      password: formState.password,
      email: formState.email || undefined,
    })

    setToken(result.access_token)
    setUser({ id: result.user_id, username: result.username })

    toast.add({ title: '注册成功', color: 'green' })
    router.push('/profile')
  } catch (err: any) {
    toast.add({ title: '注册失败', description: err.message, color: 'red' })
  } finally {
    loading.value = false
  }
}
</script>
