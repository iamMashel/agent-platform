export interface AgentRequest {
  input: string
  user_id?: string
  session_id?: string
}

export interface AgentResponse {
  input: string
  output: string | null
  tool_result: string | null
  duration_ms: number
}

export function useAgent() {
  const config = useRuntimeConfig()
  const apiUrl = config.public.apiUrl

  async function runAgent(payload: AgentRequest): Promise<AgentResponse> {
    const url = `${apiUrl}/agent/run`
    let response: Response

    try {
      response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(120_000), // 2-min hard timeout
      })
    } catch (e: unknown) {
      // Network-level failure (no response received)
      const reason = e instanceof Error ? e.message : String(e)
      const label = reason === 'The operation was aborted.' ? 'Request timed out (>2 min)' : reason
      throw new Error(`Cannot reach API at ${url} — ${label}`)
    }

    if (!response.ok) {
      let body = ''
      try { body = await response.text() } catch { /* ignore */ }
      throw new Error(`API error ${response.status} — ${body || response.statusText}`)
    }

    return response.json() as Promise<AgentResponse>
  }

  return { runAgent }
}
