export interface AgentStatus {
  id?: string
  name: string
  status: 'idle' | 'running' | 'completed' | 'error'
  message: string
  progress: number
}

export function useAgentWebSocket(sessionId: string) {
  const agents = ref<AgentStatus[]>([])
  const isConnected = ref(false)
  let ws: WebSocket | null = null

  const connect = () => {
    // Bug#10 修复：空 sessionId 不建立连接，避免路由歧义和无效 WebSocket 连接
    if (!sessionId) {
      console.warn('[WebSocket] 未提供 sessionId，跳过连接')
      return
    }
    try {
      // 相对地址：dev 由 vite /ws 代理（ws:true）转发，生产由 nginx 网关同源转发
      const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
      ws = new WebSocket(`${wsProtocol}://${window.location.host}/ws/agent-status/${sessionId}`)

      ws.onopen = () => {
        isConnected.value = true
      }

      ws.onmessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data)
          // 忽略系统消息（连接确认等），只处理 Agent 状态
          if (data.agent === '系统') return
          const idx = agents.value.findIndex((a) => a.name === data.agent)
          if (idx >= 0) {
            agents.value[idx] = {
              ...agents.value[idx],
              name: data.agent,
              status: data.status,
              message: data.message,
              progress: data.progress,
            }
          } else {
            agents.value.push({
              name: data.agent,
              status: data.status,
              message: data.message,
              progress: data.progress,
            })
          }
        } catch (e) {
          console.error('WebSocket message parse error:', e)
        }
      }

      ws.onerror = () => {
        isConnected.value = false
      }

      ws.onclose = () => {
        isConnected.value = false
        // 自动重连
        setTimeout(() => {
          if (!isConnected.value) {
            connect()
          }
        }, 3000)
      }
    } catch (e) {
      console.error('WebSocket connection error:', e)
      isConnected.value = false
    }
  }

  const disconnect = () => {
    if (ws) {
      ws.close()
      ws = null
    }
  }

  // 组件挂载时连接
  onMounted(() => {
    connect()
  })

  // 组件卸载时断开
  onUnmounted(() => {
    disconnect()
  })

  return {
    agents,
    isConnected,
    disconnect,
  }
}
