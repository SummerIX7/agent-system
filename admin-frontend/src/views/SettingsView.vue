<script setup lang="ts">
import { knowledgeApi, type KbFileItem } from '@/api/knowledge'
import {
  FolderOpenOutline,
  AddOutline,
  RefreshOutline,
  SaveOutline,
} from '@vicons/ionicons5'
import type { TreeOption, DataTableColumns } from 'naive-ui'

const message = useMessage()

const loading = ref(false)
const files = ref<KbFileItem[]>([])
const selectedDomain = ref<string>('')
const selectedCategory = ref<string>('')

// 编辑器弹窗
const showEditor = ref(false)
const editingFile = ref<any>(null)
const editorContent = ref('')
const editorPath = ref('')
const editorSaving = ref(false)

// 新建文件弹窗
const showNewFile = ref(false)
const newFileName = ref('')

// 重建索引
const rebuilding = ref(false)

// 构建领域树
const domainTree = computed<TreeOption[]>(() => {
  const map = new Map<string, Map<string, KbFileItem[]>>()
  for (const f of files.value) {
    if (!map.has(f.domain)) map.set(f.domain, new Map())
    const cats = map.get(f.domain)!
    if (!cats.has(f.category)) cats.set(f.category, [])
    cats.get(f.category)!.push(f)
  }

  return Array.from(map.entries()).map(([domain, cats]) => ({
    label: domain,
    key: `d:${domain}`,
    children: Array.from(cats.entries()).map(([cat]) => ({
      label: cat,
      key: `c:${domain}/${cat}`,
      prefix: () => h('span', { style: 'color:#9CA3AF; font-size:11px' }, `${cats.get(cat)!.length} 篇`),
    })),
  }))
})

// 当前目录下的文件
const currentFiles = computed(() => {
  return files.value.filter(f =>
    f.domain === selectedDomain.value && f.category === selectedCategory.value
  )
})

const fileColumns: DataTableColumns<KbFileItem> = [
  { title: '标题', key: 'title', width: 260, ellipsis: { tooltip: true } },
  { title: '文件名', key: 'name', width: 220, ellipsis: { tooltip: true } },
  {
    title: '大小',
    key: 'size',
    width: 80,
    render(row) { return row.size < 1024 ? `${row.size} B` : `${(row.size / 1024).toFixed(1)} KB` },
  },
  {
    title: '操作',
    key: 'actions',
    width: 160,
    render(row) {
      return h('div', { style: 'display:flex; gap:8px' }, [
        h('a', { style: 'color:#4F46E5; cursor:pointer; font-size:13px', onClick: () => openEditor(row) }, '编辑'),
        h('a', { style: 'color:#DC2626; cursor:pointer; font-size:13px', onClick: () => handleDelete(row) }, '删除'),
      ])
    },
  },
]

// 树节点点击
function handleTreeSelect(keys: string[]) {
  if (!keys.length) {
    selectedDomain.value = ''
    selectedCategory.value = ''
    return
  }
  const key = keys[0]
  if (key.startsWith('c:')) {
    const parts = key.replace('c:', '').split('/')
    selectedDomain.value = parts[0]
    selectedCategory.value = parts.slice(1).join('/')
  }
}

// 编辑文件
async function openEditor(file: KbFileItem) {
  editingFile.value = file
  editorPath.value = file.path
  try {
    const result = await knowledgeApi.readFile(file.path)
    editorContent.value = result.content
  } catch {
    editorContent.value = ''
  }
  showEditor.value = true
}

async function handleSave() {
  editorSaving.value = true
  try {
    await knowledgeApi.writeFile(editorPath.value, editorContent.value)
    message.success('保存成功')
    showEditor.value = false
    await loadData()
  } catch (err: any) {
    message.error(err.message || '保存失败')
  } finally {
    editorSaving.value = false
  }
}

// 新建文件
function openNewFile() {
  newFileName.value = ''
  editorPath.value = ''
  editorContent.value = ''
  showNewFile.value = true
}

async function handleCreateFile() {
  if (!newFileName.value.trim()) {
    message.warning('请输入文件名')
    return
  }
  if (!selectedDomain.value || !selectedCategory.value) {
    message.warning('请先选择左侧目录')
    return
  }

  const fileName = newFileName.value.endsWith('.md') ? newFileName.value : `${newFileName.value}.md`
  const fullPath = `${selectedDomain.value}/${selectedCategory.value}/${fileName}`

  try {
    await knowledgeApi.writeFile(fullPath, `---\ntitle: ${newFileName.value.replace('.md', '')}\n---\n\n# ${newFileName.value.replace('.md', '')}\n`)
    message.success('文件创建成功')
    showNewFile.value = false
    await loadData()
  } catch (err: any) {
    message.error(err.message || '创建失败')
  }
}

// 删除文件
function handleDelete(file: KbFileItem) {
  const dlg = useDialog()
  dlg.warning({
    title: '确认删除',
    content: `确定要删除 "${file.title}" 吗？此操作不可撤销。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await knowledgeApi.deleteFile(file.path)
        message.success('已删除')
        await loadData()
      } catch (err: any) {
        message.error(err.message || '删除失败')
      }
    },
  })
}

// 重建索引
async function handleRebuild() {
  rebuilding.value = true
  try {
    const result = await knowledgeApi.rebuildIndex()
    if (result.ok) {
      message.success(result.message)
    } else {
      message.error(result.message)
    }
  } catch (err: any) {
    message.error(err.message || '索引重建失败')
  } finally {
    rebuilding.value = false
  }
}

async function loadData() {
  loading.value = true
  try {
    const result = await knowledgeApi.getList()
    files.value = result.files || []
  } catch (err: any) {
    message.error(err.message || '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => loadData())
</script>

<template>
  <div>
    <div class="page-head">
      <h1 class="page-head-title">系统设置</h1>
      <p class="page-head-desc">管理知识库文件，编辑 Markdown 内容，重建向量索引</p>
    </div>

    <NGrid :cols="4" :x-gap="24" responsive="screen">
      <!-- 左侧：目录树 -->
      <NGi :span="1">
        <NCard title="知识库目录" :bordered="true" size="small" style="height: calc(100vh - 200px); overflow: auto">
          <template #header-extra>
            <NButton size="small" @click="openNewFile">
              <template #icon><NIcon><AddOutline /></NIcon></template>
              新建
            </NButton>
          </template>
          <NSpin :show="loading">
            <NTree
              v-if="domainTree.length > 0"
              :data="domainTree"
              default-expand-all
              block-line
              selectable
              @update:selected-keys="handleTreeSelect"
            />
            <NEmpty v-else description="暂无知识库文件" />
          </NSpin>
        </NCard>
      </NGi>

      <!-- 右侧：文件列表 + 索引操作 -->
      <NGi :span="3">
        <NCard :bordered="true" size="small" style="height: calc(100vh - 200px); overflow: auto">
          <template v-if="!selectedCategory">
            <div style="text-align: center; padding: 80px 0; color: #9CA3AF">
              <NIcon size="48" color="#D1D5DB"><FolderOpenOutline /></NIcon>
              <p style="margin-top: 12px">选择左侧目录查看文件</p>
            </div>
          </template>

          <template v-else>
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px">
              <div>
                <span style="font-size: 14px; font-weight: 600; color: #111827">{{ selectedDomain }}</span>
                <span style="color: #9CA3AF; margin: 0 6px">/</span>
                <span style="font-size: 13px; color: #4B5563">{{ selectedCategory }}</span>
                <NTag size="small" :bordered="false" style="margin-left: 8px">{{ currentFiles.length }} 篇</NTag>
              </div>
              <NButton size="small" @click="openNewFile">
                <template #icon><NIcon><AddOutline /></NIcon></template>
                新建文件
              </NButton>
            </div>

            <NDataTable
              :columns="fileColumns"
              :data="currentFiles"
              :bordered="false"
              size="small"
              :loading="loading"
            />
          </template>
        </NCard>

        <!-- 索引操作 -->
        <NCard :bordered="true" size="small" style="margin-top: 16px">
          <div style="display: flex; align-items: center; justify-content: space-between">
            <div>
              <div style="font-size: 14px; font-weight: 500; color: #111827">向量索引</div>
              <div style="font-size: 12px; color: #9CA3AF; margin-top: 4px">修改知识库文件后需要重建索引才能生效</div>
            </div>
            <NButton type="primary" :loading="rebuilding" @click="handleRebuild">
              <template #icon><NIcon><RefreshOutline /></NIcon></template>
              重建索引
            </NButton>
          </div>
        </NCard>
      </NGi>
    </NGrid>

    <!-- 编辑文件弹窗 -->
    <NModal v-model:show="showEditor" title="编辑文件" style="width: 900px" preset="card">
      <div style="margin-bottom: 8px; font-size: 12px; color: #9CA3AF">
        {{ editorPath }}
      </div>
      <NInput
        v-model:value="editorContent"
        type="textarea"
        :rows="24"
        style="font-family: monospace; font-size: 13px"
      />
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showEditor = false">取消</NButton>
          <NButton type="primary" :loading="editorSaving" @click="handleSave">
            <template #icon><NIcon><SaveOutline /></NIcon></template>
            保存
          </NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- 新建文件弹窗 -->
    <NModal v-model:show="showNewFile" title="新建文件" preset="card" style="width: 500px">
      <NFormItem label="保存目录" required>
        <NInput :value="selectedDomain ? `${selectedDomain}/${selectedCategory}` : '请先选择左侧目录'" disabled />
      </NFormItem>
      <NFormItem label="文件名" required>
        <NInput v-model:value="newFileName" placeholder="例如：G代码进阶技巧.md" />
      </NFormItem>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showNewFile = false">取消</NButton>
          <NButton type="primary" @click="handleCreateFile">创建</NButton>
        </NSpace>
      </template>
    </NModal>
  </div>
</template>

<style scoped>
.page-head { margin-bottom: 24px; }
.page-head-title {
  font-size: 22px; font-weight: 600; letter-spacing: -.03em;
  color: #111827; margin-bottom: 8px;
}
.page-head-desc { font-size: 14px; color: #9CA3AF; }
</style>
