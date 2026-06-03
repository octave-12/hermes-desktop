/**
 * Voice Mode Composable
 *
 * Manages the voice conversation loop:
 * 1. Keyword spotting (wake word) using browser SpeechRecognition
 * 2. Recording after wake (continuous speech-to-text)
 * 3. Sending recognized text via WebSocket
 * 4. TTS playback of AI responses
 * 5. Smart conversation ending — AI decides [CONTINUE] or [DONE]
 */
import { ref, computed } from 'vue'
import { fetchWithAuth, getBackendUrl } from '@/utils/api'
import { matchesWakeWord as pinyinMatch } from '@/data/pinyin-map'

// ── Types ────────────────────────────────────────────────────

export type VoiceModeStatus =
  | 'idle'        // Voice mode off
  | 'listening'   // Waiting for wake word
  | 'waking'      // Wake word detected, about to start recording
  | 'recording'   // Actively recording speech
  | 'processing'  // Sending recognized text
  | 'responding'  // AI is generating response
  | 'speaking'    // Playing AI response via TTS

export interface VoiceSettings {
  enabled: boolean
  wakeWord: string
  ttsVoice: string
  continuousMode: boolean  // Smart: AI decides when to end conversation
  speed: number            // TTS playback speed (0.5 ~ 2.0)
}

// ── State ────────────────────────────────────────────────────

const DEFAULT_SETTINGS: VoiceSettings = {
  enabled: false,
  wakeWord: '小马',
  ttsVoice: 'zh-CN-XiaoxiaoNeural',
  continuousMode: true,
  speed: 1.0,
}

function loadSettings(): VoiceSettings {
  try {
    const saved = localStorage.getItem('hermes_voice_settings')
    if (saved) {
      const parsed = JSON.parse(saved)
      // Migrate: remove old autoSpeak field
      delete parsed.autoSpeak
      return { ...DEFAULT_SETTINGS, ...parsed }
    }
  } catch { /* ignore */ }
  return { ...DEFAULT_SETTINGS }
}

function saveSettings(s: VoiceSettings) {
  localStorage.setItem('hermes_voice_settings', JSON.stringify(s))
}

// ── Hidden instruction appended to voice messages ────────────
// This tells the AI to include [CONTINUE] or [DONE] at the end.
// The marker is stripped before display and TTS.
const VOICE_INSTRUCTION = '\n\n<!-- 语音模式：请在回复末尾加上 [CONTINUE] 表示对话需要继续，或 [DONE] 表示本次对话已结束。判断标准：如果用户的问题已完整回答且无需追问，用 [DONE]；如果还有后续讨论空间，用 [CONTINUE]。只需在最后一行写标记即可。 -->'

const CONTINUE_MARKER = '[CONTINUE]'
const DONE_MARKER = '[DONE]'

// ── Composable ───────────────────────────────────────────────

let recognitionInstance: any = null
let continuousRecognition: any = null
let isSpeaking = false
let audioElement: HTMLAudioElement | null = null
let lastConversationDone = true  // Track if last conversation ended
let continuousIdleTimeout: ReturnType<typeof setTimeout> | null = null  // 15s idle timeout in continuous mode

// ── Streaming TTS state ──────────────────────────────────────
let streamingBuffer = ''          // Accumulated text not yet sent to TTS
let audioQueue: string[] = []     // Queued audio URLs to play sequentially
let isQueuePlaying = false        // Whether audio queue is currently playing
let streamingActive = false       // Whether streaming mode is active
let pendingTtsCount = 0           // In-flight TTS API requests
let streamingFlushed = false      // All text processed (message_done received)

export function useVoiceMode() {
  const settings = ref<VoiceSettings>(loadSettings())
  const status = ref<VoiceModeStatus>('idle')
  const interimText = ref('')
  const lastRecognizedText = ref('')
  const error = ref<string | null>(null)

  // Listen for external settings changes (from SettingsModal)
  function handleExternalSettingsChange(e: Event) {
    const detail = (e as CustomEvent).detail
    if (detail) {
      const newSettings = { ...DEFAULT_SETTINGS, ...settings.value, ...detail }
      settings.value = newSettings
      saveSettings(newSettings)
      if (!newSettings.enabled) {
        if (status.value !== 'idle') stopVoiceMode()
      } else if (newSettings.enabled && status.value === 'idle') {
        startVoiceMode()
      }
    }
  }
  window.addEventListener('voice-settings-changed', handleExternalSettingsChange)

  // Callbacks (set from outside)
  let onSendMessage: ((text: string) => void) | null = null
  let onStatusChange: ((status: VoiceModeStatus) => void) | null = null
  let onTtsComplete: ((audioUrl: string) => void) | null = null

  // ── Public config ──────────────────────────────────────────

  function configure(opts: {
    sendMessage: (text: string) => void
    onStatusChange?: (status: VoiceModeStatus) => void
    onTtsComplete?: (audioUrl: string) => void
  }) {
    onSendMessage = opts.sendMessage
    onStatusChange = opts.onStatusChange
    onTtsComplete = opts.onTtsComplete ?? null
  }

  function updateSettings(partial: Partial<VoiceSettings>) {
    settings.value = { ...settings.value, ...partial }
    saveSettings(settings.value)

    if (!settings.value.enabled) {
      stopVoiceMode()
    }
  }

  // ── Browser Speech Recognition ─────────────────────────────

  function createRecognition(): any {
    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition

    if (!SpeechRecognition) {
      error.value = '当前浏览器不支持语音识别。请使用 Chrome 或 Edge。'
      return null
    }

    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = 'zh-CN'
    return recognition
  }

  /**
   * Wake word matching with pinyin fuzzy matching.
   */
  function matchesWakeWord(transcript: string): boolean {
    const t = transcript.toLowerCase()
    const w = settings.value.wakeWord.toLowerCase()
    return pinyinMatch(t, w)
  }

  function startWakeWordDetection() {
    if (!settings.value.enabled) return

    const recognition = createRecognition()
    if (!recognition) return

    recognitionInstance = recognition
    status.value = 'listening'
    error.value = null
    interimText.value = '🎤 等待唤醒...'
    if (onStatusChange) onStatusChange(status.value)
    wakeWordDetected = false
    let lastWakeTime = 0
    const WAKE_COOLDOWN = 3000

    recognition.onresult = (event: any) => {
      let fullTranscript = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        fullTranscript += event.results[i][0].transcript
      }

      interimText.value = `🎤 听到: ${fullTranscript}`

      console.log(`[VoiceMode] Listening: "${fullTranscript}" | Looking for: "${settings.value.wakeWord}"`)

      if (
        matchesWakeWord(fullTranscript) &&
        !wakeWordDetected &&
        Date.now() - lastWakeTime > WAKE_COOLDOWN
      ) {
        wakeWordDetected = true
        lastWakeTime = Date.now()
        console.log(`[VoiceMode] ✅ Wake word "${settings.value.wakeWord}" detected in: "${fullTranscript}"`)

        status.value = 'waking'
        interimText.value = '⏳ 唤醒中...'
        if (onStatusChange) onStatusChange(status.value)

        recognition.stop()

        setTimeout(() => {
          startRecording()
        }, 400)
      }
    }

    recognition.onerror = (event: any) => {
      if (status.value === 'waking' || status.value === 'recording') return

      if (event.error === 'no-speech' || event.error === 'aborted') {
        if (settings.value.enabled && status.value === 'listening') {
          restartWakeWordDetection()
        }
        return
      }

      error.value = `语音识别错误: ${event.error}`
      console.error('[VoiceMode] Recognition error:', event.error)

      if (settings.value.enabled) {
        setTimeout(() => {
          if (settings.value.enabled) restartWakeWordDetection()
        }, 1000)
      }
    }

    recognition.onend = () => {
      if (
        settings.value.enabled &&
        status.value === 'listening' &&
        !wakeWordDetected
      ) {
        restartWakeWordDetection()
      }
    }

    try {
      recognition.start()
    } catch (e) {
      console.error('[VoiceMode] Failed to start recognition:', e)
      setTimeout(() => {
        if (settings.value.enabled) restartWakeWordDetection()
      }, 500)
    }
  }

  function startRecording() {
    if (!settings.value.enabled) return

    const rec = createRecognition()
    if (!rec) return

    continuousRecognition = rec
    status.value = 'recording'
    interimText.value = '🎙️ 请说话...'
    if (onStatusChange) onStatusChange(status.value)

    let finalTranscript = ''
    let silenceTimer: any = null
    const SILENCE_TIMEOUT = 2000

    rec.onresult = (event: any) => {
      // Clear continuous idle timeout — user started speaking
      if (continuousIdleTimeout) {
        clearTimeout(continuousIdleTimeout)
        continuousIdleTimeout = null
      }

      if (silenceTimer) clearTimeout(silenceTimer)

      let currentFinal = ''
      let currentInterim = ''

      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          currentFinal += event.results[i][0].transcript
        } else {
          currentInterim += event.results[i][0].transcript
        }
      }

      if (currentFinal) {
        finalTranscript += currentFinal
        interimText.value = finalTranscript + (currentInterim ? ` (${currentInterim})` : '')
      } else if (currentInterim) {
        interimText.value = finalTranscript + ` ${currentInterim}`
      }

      silenceTimer = setTimeout(() => {
        if (finalTranscript.trim()) {
          lastRecognizedText.value = finalTranscript.trim()
          interimText.value = '📤 发送中...'
          status.value = 'processing'
          if (onStatusChange) onStatusChange(status.value)

          // Send with hidden voice instruction appended
          const messageToSend = settings.value.continuousMode
            ? finalTranscript.trim() + VOICE_INSTRUCTION
            : finalTranscript.trim()

          if (onSendMessage) {
            onSendMessage(messageToSend)
          }

          stopContinuousRecognition()
          status.value = 'responding'
          if (onStatusChange) onStatusChange(status.value)
        } else {
          interimText.value = '🎤 等待唤醒...'
          stopContinuousRecognition()
          wakeWordDetected = false
          status.value = 'listening'
          if (onStatusChange) onStatusChange(status.value)
          restartWakeWordDetection()
        }
      }, SILENCE_TIMEOUT)
    }

    rec.onerror = (event: any) => {
      console.error('[VoiceMode] Recording error:', event.error)
      if (finalTranscript.trim()) {
        lastRecognizedText.value = finalTranscript.trim()
        const messageToSend = settings.value.continuousMode
          ? finalTranscript.trim() + VOICE_INSTRUCTION
          : finalTranscript.trim()
        if (onSendMessage) onSendMessage(messageToSend)
      }
      stopContinuousRecognition()
      wakeWordDetected = false
      status.value = 'listening'
      if (onStatusChange) onStatusChange(status.value)
      restartWakeWordDetection()
    }

    rec.onend = () => {
      if (finalTranscript.trim() && status.value === 'recording') {
        lastRecognizedText.value = finalTranscript.trim()
        const messageToSend = settings.value.continuousMode
          ? finalTranscript.trim() + VOICE_INSTRUCTION
          : finalTranscript.trim()
        if (onSendMessage) onSendMessage(messageToSend)
      }
    }

    try {
      rec.start()

      // Set 15-second idle timeout for continuous mode
      // If no speech detected within 15s, switch back to wake word detection
      if (!lastConversationDone) {
        continuousIdleTimeout = setTimeout(() => {
          console.log('[VoiceMode] 15s idle timeout — switching to wake word detection')
          continuousIdleTimeout = null
          stopContinuousRecognition()
          wakeWordDetected = false
          status.value = 'listening'
          interimText.value = '🎤 等待唤醒...'
          if (onStatusChange) onStatusChange(status.value)
          startWakeWordDetection()
        }, 15000)
      }
    } catch (e) {
      console.error('[VoiceMode] Failed to start recording:', e)
      if (continuousIdleTimeout) {
        clearTimeout(continuousIdleTimeout)
        continuousIdleTimeout = null
      }
      wakeWordDetected = false
      status.value = 'listening'
      if (onStatusChange) onStatusChange(status.value)
      restartWakeWordDetection()
    }
  }

  let wakeWordDetected = false

  function stopContinuousRecognition() {
    if (continuousIdleTimeout) {
      clearTimeout(continuousIdleTimeout)
      continuousIdleTimeout = null
    }
    if (continuousRecognition) {
      try { continuousRecognition.stop() } catch { /* ignore */ }
      continuousRecognition = null
    }
  }

  function restartWakeWordDetection() {
    stopContinuousRecognition()
    if (recognitionInstance) {
      try { recognitionInstance.stop() } catch { /* ignore */ }
      recognitionInstance = null
    }
    // Don't restart if currently speaking
    if (settings.value.enabled && !isSpeaking) {
      startWakeWordDetection()
    }
  }

  // ── Parse AI response markers ──────────────────────────────

  /**
   * Strip [CONTINUE]/[DONE] markers from text.
   * Returns { cleanText, shouldContinue }.
   */
  function parseConversationMarker(text: string): { cleanText: string, shouldContinue: boolean | null } {
    let cleanText = text
    let shouldContinue: boolean | null = null

    // Check for markers at the end of the text
    const trimmed = text.trim()
    if (trimmed.endsWith(DONE_MARKER)) {
      shouldContinue = false
      cleanText = trimmed.slice(0, -DONE_MARKER.length).trim()
    } else if (trimmed.endsWith(CONTINUE_MARKER)) {
      shouldContinue = true
      cleanText = trimmed.slice(0, -CONTINUE_MARKER.length).trim()
    }

    // Also strip any remaining markers in the middle (in case AI puts them elsewhere)
    cleanText = cleanText
      .replace(/\[CONTINUE\]/g, '')
      .replace(/\[DONE\]/g, '')
      .trim()

    // Also strip the hidden instruction comment if it leaks through
    cleanText = cleanText
      .replace(/<!--[\s\S]*?-->/g, '')
      .trim()

    return { cleanText, shouldContinue }
  }

  // ── AI Response Handling ───────────────────────────────────

  // ── Sentence boundary detection ──────────────────────────────
  // Matches Chinese sentence endings: 。！？ and newlines
  const SENTENCE_END_RE = /[^。！？!?\n]*[。！？!?\n]+/g

  /**
   * Called on each streaming token from the AI.
   * Accumulates text and sends complete sentences to TTS immediately.
   */
  function onStreamingToken(token: string) {
    if (!settings.value.enabled) return

    if (!streamingActive) {
      streamingActive = true
      streamingFlushed = false
      pendingTtsCount = 0
      streamingBuffer = ''
      audioQueue = []
      status.value = 'speaking'
      interimText.value = '🔊 播报回复...'
      if (onStatusChange) onStatusChange(status.value)
      console.log('[VoiceMode] Streaming TTS activated')
    }

    streamingBuffer += token

    // Extract ONE complete sentence at a time and send to TTS
    const regex = new RegExp(SENTENCE_END_RE.source, 'g')
    const match = regex.exec(streamingBuffer)
    if (match) {
      const sentence = match[0].trim()
      streamingBuffer = streamingBuffer.slice(match.index + match[0].length)

      if (sentence) {
        console.log(`[VoiceMode] Sentence detected, sending to TTS: "${sentence.slice(0, 60)}..."`)
        enqueueTts(sentence)
      }
    }
  }

  /**
   * Called when AI streaming is complete (message_done).
   * Flushes remaining text + conversation markers.
   */
  async function onStreamingComplete(fullText: string) {
    if (!settings.value.enabled) return

    // Parse conversation markers from full text
    const { shouldContinue } = parseConversationMarker(fullText)
    if (shouldContinue !== null) {
      lastConversationDone = !shouldContinue
      console.log(`[VoiceMode] Conversation marker: ${shouldContinue ? 'CONTINUE' : 'DONE'}`)
    } else {
      lastConversationDone = true
    }

    // Flush remaining buffer (last incomplete sentence)
    if (streamingBuffer.trim()) {
      enqueueTts(streamingBuffer.trim())
      streamingBuffer = ''
    }

    streamingActive = false
    streamingFlushed = true

    console.log(`[VoiceMode] Streaming complete, ${pendingTtsCount} TTS in-flight, queue: ${audioQueue.length}`)
    // Edge case: nothing was queued at all → complete immediately
    if (pendingTtsCount === 0 && audioQueue.length === 0 && !isQueuePlaying) {
      afterTtsComplete()
    }
    // Otherwise playQueue will detect streamingFlushed + pendingTtsCount===0 and call afterTtsComplete
  }

  /**
   * Enqueue a text segment for TTS — generates audio URL and adds to queue.
   */
  async function enqueueTts(text: string): Promise<void> {
    pendingTtsCount++
    try {
      console.log(`[VoiceMode] TTS API call for: "${text.slice(0, 40)}..."`)
      const response = await fetchWithAuth('/api/tts/speak', {
        method: 'POST',
        body: JSON.stringify({
          text,
          voice: settings.value.ttsVoice,
        }),
      })

      if (!response.ok) {
        throw new Error(`TTS API returned ${response.status}`)
      }

      const data = await response.json()
      if (!data.success || !data.audio_url) {
        throw new Error('TTS failed')
      }

      const backendUrl = getBackendUrl()
      const audioUrl = `${backendUrl}${data.audio_url}`
      console.log(`[VoiceMode] TTS audio received, queuing...`)

      if (onTtsComplete) onTtsComplete(audioUrl)

      audioQueue.push(audioUrl)

      // Start playing if not already
      if (!isQueuePlaying) {
        playQueue()
      }
    } catch (e) {
      console.error('[VoiceMode] Streaming TTS error:', e)
    } finally {
      pendingTtsCount--
    }
  }

  /**
   * Play audio queue sequentially.
   * Waits for pending TTS requests before considering playback complete.
   */
  async function playQueue() {
    if (isQueuePlaying) return
    isQueuePlaying = true
    isSpeaking = true
    console.log(`[VoiceMode] PlayQueue started, ${audioQueue.length} items in queue`)

    while (true) {
      // If queue is empty, wait briefly for new items from in-flight TTS
      if (audioQueue.length === 0) {
        // All TTS resolved + flushed + queue empty → done
        if (streamingFlushed && pendingTtsCount === 0) break
        // Still waiting for TTS results → wait 100ms then check again
        await new Promise(r => setTimeout(r, 100))
        continue
      }

      const url = audioQueue.shift()!
      try {
        await playSingleAudio(url)
      } catch (e) {
        console.error('[VoiceMode] Audio segment error:', e)
      }
    }

    console.log('[VoiceMode] PlayQueue finished')
    isQueuePlaying = false
    isSpeaking = false
    afterTtsComplete()
  }

  /**
   * Play a single audio URL, resolve when ended.
   */
  function playSingleAudio(url: string): Promise<void> {
    return new Promise<void>((resolve, reject) => {
      if (audioElement) {
        audioElement.pause()
        audioElement = null
      }

      audioElement = new Audio(url)
      audioElement.playbackRate = settings.value.speed || 1.0
      audioElement.onended = () => {
        audioElement = null
        resolve()
      }
      audioElement.onerror = (e) => {
        audioElement = null
        reject(e)
      }
      audioElement.play().catch((e) => {
        audioElement = null
        reject(e)
      })
    })
  }

  /**
   * Called externally when AI completes a response (non-streaming fallback).
   * @param text Full AI response text (may contain [CONTINUE]/[DONE] markers)
   */
  async function onAiResponse(text: string) {
    // If streaming was active, this is the message_done signal — handle via streaming complete
    if (streamingActive) {
      await onStreamingComplete(text)
      return
    }
    if (!settings.value.enabled || !text.trim()) {
      if (settings.value.enabled) {
        status.value = 'listening'
        interimText.value = '🎤 等待唤醒...'
        if (onStatusChange) onStatusChange(status.value)
        startWakeWordDetection()
      } else {
        status.value = 'idle'
        interimText.value = ''
        if (onStatusChange) onStatusChange(status.value)
      }
      return
    }

    // Parse conversation markers
    const { cleanText, shouldContinue } = parseConversationMarker(text)

    if (shouldContinue !== null) {
      lastConversationDone = !shouldContinue
      console.log(`[VoiceMode] Conversation marker: ${shouldContinue ? 'CONTINUE' : 'DONE'}`)
    } else {
      // No marker found — default to done (safe fallback)
      lastConversationDone = true
      console.log('[VoiceMode] No conversation marker found, defaulting to DONE')
    }

    // TTS the clean text (without markers)
    if (cleanText) {
      await playTts(cleanText)
    } else {
      // Nothing to speak, proceed to next action
      afterTtsComplete()
    }
  }

  async function playTts(text: string): Promise<void> {
    if (!text.trim()) return

    status.value = 'speaking'
    interimText.value = '🔊 播报回复...'
    if (onStatusChange) onStatusChange(status.value)
    isSpeaking = true

    try {
      const response = await fetchWithAuth('/api/tts/speak', {
        method: 'POST',
        body: JSON.stringify({
          text,
          voice: settings.value.ttsVoice,
        }),
      })

      if (!response.ok) {
        throw new Error(`TTS API returned ${response.status}`)
      }

      const data = await response.json()
      if (!data.success || !data.audio_url) {
        throw new Error('TTS failed')
      }

      const backendUrl = getBackendUrl()
      const audioUrl = `${backendUrl}${data.audio_url}`

      // Notify listener of the audio URL (for embedding in message)
      if (onTtsComplete) onTtsComplete(audioUrl)

      await new Promise<void>((resolve, reject) => {
        if (audioElement) {
          audioElement.pause()
          audioElement = null
        }

        audioElement = new Audio(audioUrl)
        audioElement.playbackRate = settings.value.speed || 1.0
        audioElement.onended = () => {
          isSpeaking = false
          audioElement = null
          resolve()
        }
        audioElement.onerror = (e) => {
          isSpeaking = false
          audioElement = null
          reject(e)
        }
        audioElement.play().catch((e) => {
          isSpeaking = false
          audioElement = null
          reject(e)
        })
      })
    } catch (e) {
      console.error('[VoiceMode] TTS playback error:', e)
      error.value = '语音播报失败'
    } finally {
      isSpeaking = false
      afterTtsComplete()
    }
  }

  /**
   * After TTS finishes: either auto-continue recording or go back to wake word.
   */
  function afterTtsComplete() {
    if (!settings.value.enabled) {
      status.value = 'idle'
      interimText.value = ''
      if (onStatusChange) onStatusChange(status.value)
      return
    }

    if (settings.value.continuousMode && !lastConversationDone) {
      // AI said [CONTINUE] — auto-start next recording round
      console.log('[VoiceMode] Auto-continuing conversation...')
      interimText.value = '🎙️ 请继续说...'
      status.value = 'recording'
      if (onStatusChange) onStatusChange(status.value)
      wakeWordDetected = true
      setTimeout(() => {
        if (settings.value.enabled) {
          startRecording()
        }
      }, 300)
    } else {
      // AI said [DONE] or no marker — back to wake word
      console.log('[VoiceMode] Conversation ended, waiting for wake word...')
      status.value = 'listening'
      interimText.value = '🎤 对话结束，再次唤醒继续'
      if (onStatusChange) onStatusChange(status.value)
      wakeWordDetected = false
      startWakeWordDetection()
    }
  }

  // ── Start / Stop ───────────────────────────────────────────

  function startVoiceMode() {
    if (!settings.value.enabled) return
    error.value = null
    wakeWordDetected = false
    lastConversationDone = true

    // Check browser support
    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition

    if (!SpeechRecognition) {
      error.value = '当前浏览器不支持语音识别。请使用 Chrome 或 Edge。'
      return
    }

    startWakeWordDetection()
  }

  function stopVoiceMode() {
    if (continuousIdleTimeout) {
      clearTimeout(continuousIdleTimeout)
      continuousIdleTimeout = null
    }
    if (recognitionInstance) {
      try { recognitionInstance.stop() } catch { /* ignore */ }
      recognitionInstance = null
    }
    stopContinuousRecognition()

    if (audioElement) {
      audioElement.pause()
      audioElement = null
    }

    isSpeaking = false
    wakeWordDetected = false
    status.value = 'idle'
    interimText.value = ''
    if (onStatusChange) onStatusChange(status.value)
  }

  return {
    settings,
    status,
    interimText,
    lastRecognizedText,
    error,
    configure,
    updateSettings,
    startVoiceMode,
    stopVoiceMode,
    onAiResponse,
    onStreamingToken,
    parseConversationMarker,
    isSpeaking: computed(() => status.value === 'speaking'),
    isListening: computed(() =>
      status.value === 'listening' ||
      status.value === 'recording' ||
      status.value === 'waking'
    ),
  }
}

