<template>
  <div class="voice-message-player" :class="{ playing: isPlaying, finished: isFinished }">
    <button class="play-btn" @click="togglePlay" :title="isPlaying ? '暂停' : '播放'">
      <svg v-if="!isPlaying" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
        <path d="M8 5v14l11-7z"/>
      </svg>
      <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
        <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
      </svg>
    </button>

    <div class="waveform-container" @click="seek">
      <div class="waveform-bars">
        <div
          v-for="(bar, i) in bars"
          :key="i"
          class="bar"
          :style="{ height: bar + '%', animationDelay: isPlaying ? (i * 0.05) + 's' : '0s' }"
          :class="{ active: (i / bars.length) <= progress && duration > 0 }"
        />
      </div>
      <div class="time-label">{{ displayTime }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'

const props = defineProps<{
  audioUrl: string
  autoPlay?: boolean
}>()

const emit = defineEmits<{
  (e: 'ended'): void
}>()

const isPlaying = ref(false)
const isFinished = ref(false)
const currentTime = ref(0)
const duration = ref(0)

let audio: HTMLAudioElement | null = null

// Generate static waveform bars (visual decoration)
const bars = ref<number[]>([])
function generateBars() {
  const count = 30
  bars.value = Array.from({ length: count }, () =>
    30 + Math.random() * 70
  )
}

const progress = computed(() => {
  if (duration.value <= 0) return 0
  return currentTime.value / duration.value
})

const displayTime = computed(() => {
  if (duration.value <= 0) return '0:00'
  const secs = isPlaying.value ? Math.floor(currentTime.value) : Math.floor(duration.value)
  const m = Math.floor(secs / 60)
  const s = secs % 60
  return `${m}:${s.toString().padStart(2, '0')}`
})

function togglePlay() {
  if (!audio) return

  if (isPlaying.value) {
    audio.pause()
  } else {
    if (isFinished.value) {
      audio.currentTime = 0
      isFinished.value = false
    }
    audio.play()
  }
}

function seek(e: MouseEvent) {
  if (!audio || duration.value <= 0) return
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  const x = e.clientX - rect.left
  const ratio = x / rect.width
  audio.currentTime = ratio * duration.value
}

onMounted(() => {
  generateBars()

  audio = new Audio(props.audioUrl)

  audio.addEventListener('loadedmetadata', () => {
    duration.value = audio!.duration
  })

  audio.addEventListener('timeupdate', () => {
    currentTime.value = audio!.currentTime
  })

  audio.addEventListener('play', () => {
    isPlaying.value = true
    isFinished.value = false
  })

  audio.addEventListener('pause', () => {
    isPlaying.value = false
  })

  audio.addEventListener('ended', () => {
    isPlaying.value = false
    isFinished.value = true
    emit('ended')
  })

  audio.addEventListener('error', () => {
    isPlaying.value = false
    console.error('[VoicePlayer] Audio load error')
  })

  // Auto-play
  if (props.autoPlay) {
    audio.play().catch(() => {
      // Autoplay blocked by browser — user needs to click
    })
  }
})

onUnmounted(() => {
  if (audio) {
    audio.pause()
    audio.src = ''
    audio = null
  }
})
</script>

<style scoped>
.voice-message-player {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 20px;
  margin-top: 8px;
  min-width: 180px;
  max-width: 280px;
  transition: background 0.2s;
}

.voice-message-player.playing {
  background: rgba(59, 130, 246, 0.12);
}

.voice-message-player.finished {
  opacity: 0.6;
}

.play-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: none;
  background: #3b82f6;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.2s, transform 0.1s;
}

.play-btn:hover {
  background: #2563eb;
  transform: scale(1.05);
}

.play-btn:active {
  transform: scale(0.95);
}

.waveform-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  cursor: pointer;
}

.waveform-bars {
  display: flex;
  align-items: center;
  gap: 2px;
  height: 24px;
}

.bar {
  flex: 1;
  min-width: 2px;
  border-radius: 1px;
  background: rgba(255, 255, 255, 0.2);
  transition: background 0.15s;
}

.bar.active {
  background: #3b82f6;
}

.playing .bar {
  animation: pulse 0.8s ease-in-out infinite alternate;
}

@keyframes pulse {
  from { opacity: 0.7; }
  to { opacity: 1; }
}

.time-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
  text-align: right;
  font-variant-numeric: tabular-nums;
}
</style>
