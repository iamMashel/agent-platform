<template>
  <div class="max-w-4xl mx-auto px-4 py-8">
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-white">System Status</h1>
      <p class="text-sm text-gray-500 mt-1">Live health and observability links for the platform</p>
    </div>

    <!-- API Health Card -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
      <div class="bg-gray-900 border border-gray-800 rounded-2xl p-5">
        <div class="flex items-center justify-between mb-3">
          <span class="text-xs font-semibold uppercase tracking-wider text-gray-500">API Status</span>
          <span
            class="w-2.5 h-2.5 rounded-full"
            :class="{
              'bg-emerald-400 shadow-[0_0_6px] shadow-emerald-400': health.status === 'ok',
              'bg-red-400': health.status === 'error',
              'bg-yellow-400 animate-pulse': health.status === 'loading',
            }"
          />
        </div>
        <p class="text-2xl font-bold" :class="health.status === 'ok' ? 'text-emerald-400' : health.status === 'error' ? 'text-red-400' : 'text-yellow-400'">
          {{ health.status === 'ok' ? 'Healthy' : health.status === 'error' ? 'Down' : 'Checking…' }}
        </p>
        <p v-if="health.latency_ms !== undefined" class="text-xs text-gray-500 mt-1 font-mono">
          {{ health.latency_ms }}ms latency
        </p>
        <p v-if="health.error" class="text-xs text-red-400 mt-1 truncate" :title="health.error">
          {{ health.error }}
        </p>
      </div>

      <div class="bg-gray-900 border border-gray-800 rounded-2xl p-5">
        <div class="mb-3">
          <span class="text-xs font-semibold uppercase tracking-wider text-gray-500">Environment</span>
        </div>
        <p class="text-2xl font-bold text-white capitalize">{{ health.env || '—' }}</p>
        <p class="text-xs text-gray-500 mt-1">{{ health.app || 'Agent Platform' }}</p>
      </div>

      <div class="bg-gray-900 border border-gray-800 rounded-2xl p-5 flex flex-col justify-between">
        <div class="mb-3">
          <span class="text-xs font-semibold uppercase tracking-wider text-gray-500">Last Check</span>
        </div>
        <p class="text-sm text-gray-300 font-mono">{{ lastChecked }}</p>
        <button
          @click="checkHealth"
          class="mt-3 text-xs px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 transition-colors border border-gray-700"
        >
          Refresh
        </button>
      </div>
    </div>

    <!-- Observability links -->
    <h2 class="text-sm font-semibold uppercase tracking-wider text-gray-500 mb-3">Observability Stack</h2>
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
      <a
        v-for="link in observabilityLinks"
        :key="link.name"
        :href="link.url"
        target="_blank"
        rel="noopener noreferrer"
        class="group bg-gray-900 border border-gray-800 hover:border-gray-600 rounded-2xl p-5 transition-all flex items-start gap-4"
      >
        <div class="w-10 h-10 rounded-xl flex items-center justify-center text-xl flex-shrink-0" :style="{ background: link.bg }">
          {{ link.icon }}
        </div>
        <div>
          <p class="font-semibold text-sm text-white group-hover:text-blue-400 transition-colors">{{ link.name }}</p>
          <p class="text-xs text-gray-500 mt-0.5">{{ link.description }}</p>
          <p class="text-xs text-gray-600 font-mono mt-1">{{ link.url }}</p>
        </div>
      </a>
    </div>

    <!-- Service table -->
    <h2 class="text-sm font-semibold uppercase tracking-wider text-gray-500 mb-3">Service Endpoints</h2>
    <div class="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-gray-800">
            <th class="text-left px-5 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Endpoint</th>
            <th class="text-left px-5 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Method</th>
            <th class="text-left px-5 py-3 text-xs font-semibold uppercase tracking-wider text-gray-500">Description</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="ep in endpoints"
            :key="ep.path"
            class="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/40 transition-colors"
          >
            <td class="px-5 py-3 font-mono text-blue-400">{{ ep.path }}</td>
            <td class="px-5 py-3">
              <span
                class="text-xs font-mono px-2 py-0.5 rounded"
                :class="ep.method === 'POST' ? 'bg-green-500/10 text-green-400' : 'bg-blue-500/10 text-blue-400'"
              >
                {{ ep.method }}
              </span>
            </td>
            <td class="px-5 py-3 text-gray-400">{{ ep.description }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const { health, checkHealth } = useHealth()
const config = useRuntimeConfig()
const apiUrl = config.public.apiUrl

const lastChecked = computed(() => {
  return new Date().toLocaleTimeString()
})

const observabilityLinks = [
  {
    name: 'Grafana',
    description: 'Metrics & dashboards',
    url: 'http://localhost:3001',
    icon: '📊',
    bg: 'rgba(242, 73, 92, 0.15)',
  },
  {
    name: 'Langfuse',
    description: 'LLM traces & evals',
    url: 'http://localhost:3000',
    icon: '🔍',
    bg: 'rgba(87, 148, 242, 0.15)',
  },
  {
    name: 'Prometheus',
    description: 'Raw metrics scraper',
    url: 'http://localhost:9090',
    icon: '🔥',
    bg: 'rgba(255, 149, 0, 0.15)',
  },
]

const endpoints = [
  { path: '/health', method: 'GET', description: 'Health check — returns status, app, env' },
  { path: '/metrics', method: 'GET', description: 'Prometheus metrics text format' },
  { path: '/agent/run', method: 'POST', description: 'Execute the LangGraph agent workflow' },
  { path: '/docs', method: 'GET', description: 'Interactive OpenAPI documentation' },
]

useHead({ title: 'Status — Agent Platform' })
</script>
