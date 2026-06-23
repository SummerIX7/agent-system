<template>
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold mb-6">学习者画像输入</h1>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <!-- 基本信息表单 -->
      <UCard>
        <template #header>
          <h2 class="text-lg font-semibold">基本信息</h2>
        </template>

        <UForm :state="formState" class="space-y-4">
          <UFormGroup label="学历背景" name="education_background">
            <USelect
              v-model="formState.education_background"
              :options="['高中', '大专', '本科', '硕士', '博士']"
              placeholder="请选择学历背景"
            />
          </UFormGroup>

          <UFormGroup label="专业方向" name="major">
            <UInput v-model="formState.major" placeholder="如：计算机科学、数据科学" />
          </UFormGroup>

          <UFormGroup label="工作经验（年）" name="work_experience_years">
            <UInput
              v-model="formState.work_experience_years"
              type="number"
              placeholder="0"
            />
          </UFormGroup>

          <UFormGroup label="学习风格" name="learning_style">
            <USelect
              v-model="formState.learning_style"
              :options="[
                { label: '视觉型', value: 'visual' },
                { label: '理论型', value: 'theory' },
                { label: '实践型', value: 'practice' },
              ]"
              option-attribute="label"
              value-attribute="value"
              placeholder="请选择学习风格"
            />
          </UFormGroup>
        </UForm>
      </UCard>

      <!-- 自评表单 -->
      <UCard>
        <template #header>
          <h2 class="text-lg font-semibold">技能自评</h2>
        </template>

        <div class="space-y-4">
          <div v-for="skill in skillOptions" :key="skill" class="flex items-center justify-between">
            <span class="text-sm font-medium">{{ skill }}</span>
            <USelect
              v-model="formState.self_assessment[skill]"
              :options="['不了解', '了解基础', '熟练', '精通']"
              class="w-40"
            />
          </div>
        </div>
      </UCard>
    </div>

    <!-- 学习目标 -->
    <UCard class="mt-8">
      <template #header>
        <h2 class="text-lg font-semibold">学习目标</h2>
      </template>

      <div class="space-y-3">
        <div v-for="(goal, index) in formState.goals" :key="index" class="flex gap-2">
          <UInput v-model="formState.goals[index]" placeholder="请输入学习目标" class="flex-1" />
          <UButton color="red" variant="ghost" icon="i-heroicons-trash" @click="removeGoal(index)" />
        </div>
        <UButton variant="ghost" icon="i-heroicons-plus" @click="addGoal">
          添加目标
        </UButton>
      </div>
    </UCard>

    <!-- 提交按钮 -->
    <div class="mt-8 text-center">
      <UButton size="lg" :loading="loading" @click="submitProfile">
        提交画像，开始诊断
      </UButton>
    </div>
  </div>
</template>

<script setup lang="ts">
const router = useRouter()
const api = useApi()
const { setSession, setProfile } = useSession()
const loading = ref(false)

const skillOptions = [
  'Python 基础',
  'NumPy',
  'Pandas',
  'Matplotlib',
  '统计学基础',
  'SQL 数据库',
  '数据清洗',
  '机器学习基础',
]

const formState = reactive({
  education_background: '',
  major: '',
  work_experience_years: 0,
  learning_style: '',
  self_assessment: {} as Record<string, string>,
  goals: [''],
})

const addGoal = () => {
  formState.goals.push('')
}

const removeGoal = (index: number) => {
  formState.goals.splice(index, 1)
}

const submitProfile = async () => {
  if (!formState.education_background || !formState.major) {
    alert('请填写学历背景和专业方向')
    return
  }

  loading.value = true
  try {
    const result = await api.createProfile({
      education_background: formState.education_background,
      major: formState.major,
      work_experience_years: formState.work_experience_years,
      self_assessment: formState.self_assessment,
      learning_style: formState.learning_style || 'practice',
      goals: formState.goals.filter(g => g.trim()),
    })

    // 存入全局状态
    setSession(result.id, result.id)  // session_id 暂用 learner_id
    setProfile(result)

    router.push('/dashboard')
  } catch (err: any) {
    console.error('提交失败:', err)
    alert(`提交失败: ${err.message}`)
  } finally {
    loading.value = false
  }
}
</script>
