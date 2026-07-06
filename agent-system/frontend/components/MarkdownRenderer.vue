<template>
  <div class="markdown-body" v-html="renderedHtml" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import katex from 'katex'
import 'katex/dist/katex.min.css'

// 配置 marked
marked.setOptions({
  breaks: true,
  gfm: true,
})

// 自定义渲染器
const renderer = new marked.Renderer()

// 代码块高亮
renderer.code = function({ text, lang }: { text: string; lang?: string }) {
  let highlighted: string
  if (lang && hljs.getLanguage(lang)) {
    highlighted = hljs.highlight(text, { language: lang }).value
  } else {
    highlighted = hljs.highlightAuto(text).value
  }
  return `<pre><code class="hljs language-${lang || 'auto'}">${highlighted}</code></pre>`
}

// 行内代码
renderer.codespan = function({ text }: { text: string }) {
  return `<code class="inline-code">${text}</code>`
}

// 链接在新窗口打开
renderer.link = function({ href, title, text }: { href: string; title?: string; text: string }) {
  const titleAttr = title ? ` title="${title}"` : ''
  return `<a href="${href}"${titleAttr} target="_blank" rel="noopener noreferrer">${text}</a>`
}

// 图片样式
renderer.image = function({ href, title, text }: { href: string; title?: string; text: string }) {
  const titleAttr = title ? ` title="${title}"` : ''
  return `<img src="${href}" alt="${text}"${titleAttr} class="markdown-image" />`
}

// marked 新版传入 Table token，由默认渲染器解析单元格后再包裹滚动容器。
const defaultTableRenderer = renderer.table
renderer.table = function(this: any, token: any) {
  return `<div class="table-wrapper">${defaultTableRenderer.call(this, token)}</div>`
}

// 设置渲染器
marked.use({ renderer })

const props = defineProps<{
  content: string
}>()

// 处理 LaTeX 公式
const processLatex = (text: string): string => {
  // 块级公式 $$...$$
  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, formula) => {
    try {
      return katex.renderToString(formula.trim(), { displayMode: true })
    } catch (e) {
      return `<pre class="latex-error">LaTeX Error: ${e}</pre>`
    }
  })

  // 行内公式 $...$
  text = text.replace(/\$([^\$\n]+?)\$/g, (_, formula) => {
    try {
      return katex.renderToString(formula.trim(), { displayMode: false })
    } catch (e) {
      return `<code class="latex-error">${formula}</code>`
    }
  })

  return text
}

// 渲染 Markdown
const renderedHtml = computed(() => {
  if (!props.content) return '<p class="text-text-3">暂无内容</p>'

  // 预处理 LaTeX 公式
  let processedContent = processLatex(props.content)

  // 渲染 Markdown
  return marked.parse(processedContent) as string
})
</script>

<style>
/* Markdown 内容样式 */
.markdown-body {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-2);
}

.markdown-body h1 {
  font-size: 22px;
  font-weight: 600;
  color: var(--text);
  margin: 28px 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--line);
}

.markdown-body h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text);
  margin: 24px 0 10px;
}

.markdown-body h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin: 18px 0 8px;
}

.markdown-body h4 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin: 14px 0 6px;
}

.markdown-body p {
  margin-bottom: 12px;
}

.markdown-body strong {
  color: var(--text);
  font-weight: 600;
}

.markdown-body em {
  font-style: italic;
}

.markdown-body a {
  color: var(--accent);
  text-decoration: none;
}

.markdown-body a:hover {
  text-decoration: underline;
}

.markdown-body ul,
.markdown-body ol {
  padding-left: 24px;
  margin-bottom: 12px;
}

.markdown-body li {
  margin-bottom: 4px;
}

.markdown-body li > ul,
.markdown-body li > ol {
  margin-top: 4px;
  margin-bottom: 0;
}

/* 行内代码 */
.markdown-body .inline-code {
  font-family: var(--mono), 'Consolas', 'Courier New', monospace;
  font-size: 12.5px;
  background: var(--bg-muted);
  padding: 2px 6px;
  border-radius: 4px;
  color: #E83E8C;
}

/* 代码块 */
.markdown-body pre {
  font-family: var(--mono), 'Consolas', 'Courier New', monospace;
  font-size: 13px;
  background: #1E1B2E;
  color: #E5E7EB;
  padding: 16px 18px;
  border-radius: var(--radius-sm);
  overflow-x: auto;
  line-height: 1.6;
  margin-bottom: 16px;
}

.markdown-body pre code {
  background: none;
  padding: 0;
  color: inherit;
  font-size: inherit;
}

/* 引用块 */
.markdown-body blockquote {
  border-left: 4px solid var(--accent);
  padding: 12px 16px;
  margin: 16px 0;
  background: var(--accent-soft);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.markdown-body blockquote p:last-child {
  margin-bottom: 0;
}

/* 水平线 */
.markdown-body hr {
  border: none;
  border-top: 1px solid var(--line);
  margin: 24px 0;
}

/* 表格 */
.markdown-body .table-wrapper {
  overflow-x: auto;
  margin-bottom: 16px;
}

.markdown-body table {
  width: 100%;
  border-collapse: collapse;
}

.markdown-body th,
.markdown-body td {
  padding: 10px 12px;
  border: 1px solid var(--line);
  text-align: left;
}

.markdown-body th {
  background: var(--bg-muted);
  font-weight: 600;
  color: var(--text);
}

.markdown-body tr:nth-child(even) {
  background: var(--bg-soft);
}

.markdown-body tr:hover {
  background: var(--accent-soft);
}

/* 图片 */
.markdown-body .markdown-image {
  max-width: 100%;
  height: auto;
  border-radius: var(--radius-sm);
  margin: 8px 0;
}

/* LaTeX 错误 */
.markdown-body .latex-error {
  color: var(--err);
  background: var(--err-soft);
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  font-size: 12px;
}

/* 来源标签样式（保持与原有设计一致） */
.markdown-body .source-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  color: var(--accent);
  background: var(--accent-soft);
  padding: 3px 9px;
  border-radius: 4px;
  margin: 0 4px;
}

/* 响应式 */
@media (max-width: 768px) {
  .markdown-body {
    font-size: 13px;
  }

  .markdown-body h1 {
    font-size: 20px;
  }

  .markdown-body h2 {
    font-size: 16px;
  }

  .markdown-body h3 {
    font-size: 14px;
  }

  .markdown-body pre {
    font-size: 12px;
    padding: 12px 14px;
  }
}
</style>
