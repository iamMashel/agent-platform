<template>
  <div class="min-h-screen bg-gray-950 text-gray-100 font-inter">
    <!-- Nav -->
    <nav class="border-b border-gray-800 bg-gray-950/80 backdrop-blur sticky top-0 z-50">
      <div class="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
        <NuxtLink to="/" class="flex items-center gap-2 group">
          <div class="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-emerald-500 flex items-center justify-center text-xs font-bold">
            AP
          </div>
          <span class="font-semibold text-sm tracking-tight group-hover:text-white transition-colors">
            Agent Platform
          </span>
        </NuxtLink>

        <div class="flex items-center gap-1">
          <NuxtLink
            to="/"
            class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
            :class="$route.path === '/' ? 'bg-gray-800 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800/50'"
          >
            Chat
          </NuxtLink>
          <NuxtLink
            to="/status"
            class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
            :class="$route.path === '/status' ? 'bg-gray-800 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800/50'"
          >
            Status
          </NuxtLink>
        </div>
      </div>
    </nav>

    <!-- Page content -->
    <slot />
  </div>
</template>
