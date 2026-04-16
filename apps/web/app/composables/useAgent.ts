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
    const response = await fetch(`${apiUrl}/agent/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Agent error (${response.status}): ${error}`)
    }

    return response.json() as Promise<AgentResponse>
  }

  return { runAgent }
}
