export interface HealthStatus {
  status: 'ok' | 'error' | 'loading'
  app?: string
  env?: string
  latency_ms?: number
  error?: string
}

export function useHealth() {
  const config = useRuntimeConfig()
  const apiUrl = config.public.apiUrl
  const health = ref<HealthStatus>({ status: 'loading' })

  async function checkHealth(): Promise<void> {
    const start = Date.now()
    const url = `${apiUrl}/health`
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(10_000) })
      const latency_ms = Date.now() - start

      if (!response.ok) {
        health.value = { status: 'error', error: `HTTP ${response.status} from ${url}`, latency_ms }
        return
      }

      const data = await response.json()
      health.value = { status: 'ok', ...data, latency_ms }
    } catch (e: unknown) {
      const reason = e instanceof Error ? e.message : 'Connection failed'
      health.value = {
        status: 'error',
        error: `${url} — ${reason}`,
        latency_ms: Date.now() - start,
      }
    }
  }

  // Poll every 30s
  onMounted(() => {
    checkHealth()
    const timer = setInterval(checkHealth, 30_000)
    onUnmounted(() => clearInterval(timer))
  })

  return { health, checkHealth }
}
