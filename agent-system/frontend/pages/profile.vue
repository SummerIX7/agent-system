<template>
  <div class="page">
    <div class="page-head">
      <p class="page-head__eyebrow">Step 1</p>
      <h1 class="page-head__title">学习者画像</h1>
      <p class="page-head__desc">请填写您的学习背景和目标，以便系统为您生成个性化学习资源。画像越准确，学情诊断与资源生成就越贴合您的实际水平。</p>
    </div>

    <div class="profile-grid">
      <!-- 基本信息 -->
      <div class="card">
        <div class="card__head">
          <h2 class="card__title">基本信息</h2>
        </div>

        <div class="field">
          <label class="field__label">学历背景 <span style="color: var(--err)">*</span></label>
          <select v-model="formState.education_background" class="select">
            <option value="高中">高中</option>
            <option value="大专">大专</option>
            <option value="本科">本科</option>
            <option value="硕士">硕士</option>
            <option value="博士">博士</option>
          </select>
        </div>

        <div class="field">
          <label class="field__label">专业方向 <span style="color: var(--err)">*</span></label>
          <input v-model="formState.major" class="input" placeholder="如：机械工程、数控技术、模具设计">
        </div>

        <div class="field">
          <label class="field__label">工作经验（年）</label>
          <input v-model.number="formState.work_experience_years" class="input" type="number" placeholder="0">
        </div>

        <div class="field">
          <label class="field__label">学习领域 <span style="color: var(--err)">*</span></label>
          <select v-model="formState.domain" class="select" @change="onDomainChange">
            <option v-for="d in domains" :key="d.code" :value="d.code">{{ d.name }}</option>
          </select>
        </div>

        <div class="field" style="margin-bottom: 0">
          <label class="field__label">学习风格</label>
          <select v-model="formState.learning_style" class="select">
            <option value="visual">视觉型</option>
            <option value="theory">理论型</option>
            <option value="practice">实践型</option>
          </select>
        </div>
      </div>

      <!-- 技能自评 -->
      <div class="card">
        <div class="card__head">
          <h2 class="card__title">技能自评</h2>
          <span class="card__sub">如实评估，系统将据此定位盲区</span>
        </div>
        <div v-for="skill in skillOptions" :key="skill" class="skill-row">
          <div>
            <div style="font-size: 13.5px; font-weight: 500">{{ skill }}</div>
          </div>
          <select v-model="formState.self_assessment[skill]" class="select" style="width: 130px; padding: 7px 10px; font-size: 13px">
            <option value="不了解">不了解</option>
            <option value="了解基础">了解基础</option>
            <option value="熟练">熟练</option>
            <option value="精通">精通</option>
          </select>
        </div>
      </div>
    </div>

    <!-- 学习目标 -->
    <div class="card" style="margin-top: 24px">
      <div class="card__head">
        <h2 class="card__title">学习目标</h2>
        <button class="btn btn--text btn--sm" @click="addGoal">+ 添加目标</button>
      </div>
      <div v-for="(goal, idx) in formState.goals" :key="idx" class="goal-row">
        <input v-model="formState.goals[idx]" class="input" style="flex: 1" placeholder="请输入学习目标">
        <button class="btn btn--ghost btn--sm" @click="removeGoal(idx)">删除</button>
      </div>
    </div>

    <div style="text-align: center; margin-top: 32px">
      <button class="btn btn--primary btn--lg" :disabled="loading" @click="submitProfile">
        {{ profileLoaded ? '更新画像，重新诊断' : '提交画像，开始诊断' }} →
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DomainConfig } from '~/types/api'

const router = useRouter()
const api = useApi()
const toast = useToast()
const { isLoggedIn, isLoading: authLoading } = useAuth()
const { setSession, setProfile } = useSession()
const loading = ref(false)
const profileLoaded = ref(false)

// 领域列表
const domains = ref<DomainConfig[]>([])

// 等认证状态恢复后再判断
watch(authLoading, async (val) => {
  if (!val && !isLoggedIn.value) {
    router.push('/login')
  }
}, { immediate: true })

// 登录后自动加载已有画像 + 领域列表
onMounted(async () => {
  if (!isLoggedIn.value) return

  // 加载可用领域
  try {
    domains.value = await api.getDomains()
  } catch {
    console.warn('加载领域列表失败')
  }

  // 加载已有画像
  try {
    const existing = await api.getMyProfile()
    if (existing) {
      setSession(existing.session_id || `user-${existing.id}`, String(existing.id))
      setProfile(existing)
      // 预填表单
      formState.education_background = existing.education_background || '本科'
      formState.major = existing.major || ''
      formState.work_experience_years = existing.work_experience_years || 0
      formState.learning_style = existing.learning_style || 'practice'
      formState.domain = (existing as any).domain || 'cnc'
      formState.self_assessment = existing.self_assessment || {}
      formState.goals = existing.goals?.length ? existing.goals : ['']
      profileLoaded.value = true
    }
  } catch {
    // 404 = 没有画像，正常情况
  }
})

// 当前领域的技能自评项
const skillOptions = computed(() => {
  const selected = domains.value.find(d => d.code === formState.domain)
  return selected?.self_assessment_skills || []
})

// 领域切换时重置技能评估
function onDomainChange() {
  formState.self_assessment = {}
}

const formState = reactive({
  education_background: '本科',
  major: '',
  work_experience_years: 0,
  learning_style: 'practice',
  domain: 'cnc',
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
    toast.add({
      title: '请填写必填项',
      description: '学历背景和专业方向为必填',
      color: 'orange',
    })
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
      domain: formState.domain || undefined,
    })

    // 存入全局状态
    setSession(result.session_id || `user-${result.id}`, String(result.id))
    setProfile(result)

    toast.add({ title: '画像已提交，正在启动学情诊断...', color: 'primary' })
    router.push('/dashboard')
  } catch (err: any) {
    console.error('提交失败:', err)
    toast.add({
      title: '提交失败',
      description: err.message || '请稍后重试',
      color: 'red',
    })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.profile-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}
.skill-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 0;
  border-bottom: 1px solid var(--line);
}
.skill-row:last-child {
  border-bottom: none;
}
.goal-row {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}
@media (max-width: 760px) {
  .profile-grid { grid-template-columns: 1fr; }
}
</style>
