<template>
  <div class="flex flex-col h-[calc(100vh-57px)]">
    <!-- Session header -->
    <div class="flex items-center justify-between px-4 py-2 border-b border-gray-800/60 bg-gray-950">
      <span class="text-[11px] text-gray-500 font-mono">
        Session: <span class="text-gray-400">{{ sessionId }}</span>
      </span>
      <button
        @click="newSession"
        class="text-[11px] text-gray-500 hover:text-gray-300 transition-colors px-2 py-1 rounded-lg hover:bg-gray-800"
      >
        + New chat
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-4 py-6 space-y-4 custom-scrollbar" ref="chatContainer">
      <!-- Empty state -->
      <div v-if="messages.length === 0" class="flex flex-col items-center justify-center h-full gap-4 text-center">
        <div class="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-emerald-500 flex items-center justify-center text-2xl">
          🤖
        </div>
        <div>
          <p class="text-lg font-semibold text-white">How can I help you?</p>
          <p class="text-sm text-gray-500 mt-1">Powered by LangGraph + Gemini</p>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2 max-w-md w-full">
          <button
            v-for="prompt in suggestedPrompts"
            :key="prompt"
            @click="sendMessage(prompt)"
            class="text-left text-sm px-4 py-3 rounded-xl border border-gray-700 text-gray-300 hover:border-blue-500 hover:text-white hover:bg-blue-500/5 transition-all"
          >
            {{ prompt }}
          </button>
        </div>
      </div>

      <!-- Messages -->
      <template v-else>
        <div
          v-for="(msg, i) in messages"
          :key="i"
          class="flex w-full"
          :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
        >
          <div
            class="max-w-[82%] rounded-2xl px-4 py-3 shadow-sm"
            :class="
              msg.role === 'user'
                ? 'bg-blue-600 text-white rounded-br-sm'
                : 'bg-gray-800 text-gray-100 rounded-bl-sm border border-gray-700/60'
            "
          >
            <div class="text-[11px] font-semibold uppercase tracking-wider mb-1.5 opacity-60">
              {{ msg.role === 'user' ? 'You' : 'Agent' }}
            </div>
            <div class="leading-relaxed text-sm md-content" v-html="renderMarkdown(msg.content)" />
            <!-- Tool result badge -->
            <div v-if="msg.tool_result" class="mt-2">
              <details class="text-xs">
                <summary class="cursor-pointer text-emerald-400 hover:text-emerald-300 font-medium">
                  🔍 Tool result
                </summary>
                <pre class="mt-1.5 p-2 bg-gray-900/60 rounded-lg text-gray-400 whitespace-pre-wrap overflow-auto text-[11px]">{{ msg.tool_result }}</pre>
              </details>
            </div>
            <!-- Latency badge -->
            <div v-if="msg.duration_ms !== undefined" class="mt-2 flex justify-end">
              <span class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                ⚡ {{ msg.duration_ms }}ms
              </span>
            </div>
          </div>
        </div>

        <!-- Loading indicator -->
        <div v-if="loading" class="flex justify-start">
          <div class="bg-gray-800 border border-gray-700/60 rounded-2xl rounded-bl-sm px-4 py-3 flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style="animation-delay:0ms" />
            <span class="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style="animation-delay:150ms" />
            <span class="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style="animation-delay:300ms" />
          </div>
        </div>

        <!-- Error banner -->
        <div v-if="error" class="flex justify-center">
          <div class="flex items-center gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-2.5">
            <span>⚠️</span>
            <span>{{ error }}</span>
            <button @click="error = null" class="ml-2 opacity-60 hover:opacity-100">✕</button>
          </div>
        </div>
      </template>
    </div>

    <!-- Input bar -->
    <div class="border-t border-gray-800 bg-gray-950 px-4 py-4">
      <div class="max-w-3xl mx-auto">
        <form @submit.prevent="() => sendMessage()" class="flex gap-2 items-end">
          <div class="flex-1 relative">
            <textarea
              v-model="inputText"
              rows="1"
              placeholder="Ask the agent anything..."
              class="w-full resize-none bg-gray-800 border border-gray-700 rounded-xl py-3 pl-4 pr-4 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 transition-all leading-relaxed"
              :disabled="loading"
              @keydown.enter.exact.prevent="() => sendMessage()"
              @keydown.enter.shift.exact="() => {}"
              style="min-height: 44px; max-height: 160px; field-sizing: content;"
            />
          </div>
          <button
            type="submit"
            :disabled="!inputText.trim() || loading"
            class="h-11 w-11 flex-shrink-0 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:cursor-not-allowed transition-colors flex items-center justify-center shadow-sm"
          >
            <svg class="w-4 h-4 text-white" viewBox="0 0 20 20" fill="currentColor">
              <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
            </svg>
          </button>
        </form>
        <p class="text-center text-[11px] text-gray-600 mt-2">
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { marked } from 'marked'

marked.setOptions({ breaks: true })

function renderMarkdown(text: string): string {
  return marked.parse(text) as string
}

const SESSION_KEY = 'agent-session-id'

const { runAgent } = useAgent()
const chatContainer = ref<HTMLElement | null>(null)

interface Message {
  role: 'user' | 'agent'
  content: string
  tool_result?: string | null
  duration_ms?: number
}

const messages = ref<Message[]>([])
const inputText = ref('')
const loading = ref(false)
const error = ref<string | null>(null)

const storedId = import.meta.client ? localStorage.getItem(SESSION_KEY) : null
const sessionId = ref(storedId || `session-${Date.now()}`)
if (import.meta.client) {
  watch(sessionId, (id) => localStorage.setItem(SESSION_KEY, id), { immediate: true })
}

const suggestedPrompts = [
  'Search for the latest AI news',
  'What is LangGraph?',
  'Explain observability in production systems',
  'What are the best practices for LLM deployment?',
]

async function sendMessage(text?: string): Promise<void> {
  const userText = text ?? inputText.value.trim()
  if (!userText || loading.value) return

  messages.value.push({ role: 'user', content: userText })
  inputText.value = ''
  loading.value = true
  error.value = null

  await nextTick()
  scrollToBottom()

  try {
    const result = await runAgent({
      input: userText,
      session_id: sessionId.value,
    })

    messages.value.push({
      role: 'agent',
      content: result.output ?? result.tool_result ?? '(empty response)',
      tool_result: result.tool_result,
      duration_ms: result.duration_ms,
    })
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Unknown error'
  } finally {
    loading.value = false
    await nextTick()
    scrollToBottom()
  }
}

function scrollToBottom(): void {
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

function newSession(): void {
  messages.value = []
  error.value = null
  sessionId.value = `session-${Date.now()}`
}
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #374151; border-radius: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #4b5563; }

/* Markdown content styling */
.md-content :deep(p) { margin: 0.35em 0; }
.md-content :deep(p:first-child) { margin-top: 0; }
.md-content :deep(p:last-child) { margin-bottom: 0; }
.md-content :deep(strong) { font-weight: 600; color: #f9fafb; }
.md-content :deep(em) { font-style: italic; }
.md-content :deep(code) { background: #111827; border-radius: 4px; padding: 1px 5px; font-size: 0.8em; font-family: ui-monospace, monospace; color: #a5b4fc; }
.md-content :deep(pre) { background: #111827; border-radius: 8px; padding: 10px 14px; overflow-x: auto; margin: 0.5em 0; }
.md-content :deep(pre code) { background: transparent; padding: 0; font-size: 0.78em; color: #d1d5db; }
.md-content :deep(ul) { list-style: disc; padding-left: 1.4em; margin: 0.4em 0; }
.md-content :deep(ol) { list-style: decimal; padding-left: 1.4em; margin: 0.4em 0; }
.md-content :deep(li) { margin: 0.15em 0; }
.md-content :deep(h1), .md-content :deep(h2), .md-content :deep(h3) { font-weight: 600; color: #f9fafb; margin: 0.6em 0 0.3em; }
.md-content :deep(h1) { font-size: 1.15em; }
.md-content :deep(h2) { font-size: 1.05em; }
.md-content :deep(h3) { font-size: 0.95em; }
.md-content :deep(blockquote) { border-left: 3px solid #4b5563; padding-left: 0.75em; color: #9ca3af; margin: 0.4em 0; }
.md-content :deep(a) { color: #60a5fa; text-decoration: underline; }
.md-content :deep(hr) { border-color: #374151; margin: 0.5em 0; }
</style>
