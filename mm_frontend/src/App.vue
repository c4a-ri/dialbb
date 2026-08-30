<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

type ClientState = 'idle' | 'starting' | 'running' | 'stopping' | 'error'

type WebAudioWindow = Window & {
  webkitAudioContext?: typeof AudioContext
}

interface AudioPayload {
  audio: string
  utteranceId: number
  segmentIndex: number
  segmentCount: number
}

interface ChatMessage {
  role: 'user' | 'system'
  text: string
}

const AUX_DATA_DEBUG = {
  debug: true,
  source: 'pwa_mobile_client'
}

const MIC_VISUAL_BOOST = 2.6
const TTS_VISUAL_BOOST = 1.0
const BASE_WAVE_FLOOR = 0.03

const state = ref<ClientState>('idle')
const statusText = ref('待機中')
const errorText = ref('')
const chatMessages = ref<ChatMessage[]>([])

const canvasRef = ref<HTMLCanvasElement | null>(null)
const chatOverlayRef = ref<HTMLDivElement | null>(null)

const isBusy = computed(() => state.value === 'starting' || state.value === 'stopping')
const isActive = computed(() => state.value === 'running' || state.value === 'starting' || state.value === 'stopping')
const buttonLabel = computed(() => (isActive.value ? '終了' : '開始'))

function pushChatMessage(role: 'user' | 'system', text: string): void {
  const normalized = text.trim()
  if (!normalized) {
    return
  }
  chatMessages.value.push({ role, text: normalized })
  if (chatMessages.value.length > 10) {
    chatMessages.value.shift()
  }
  void nextTick(() => {
    const overlay = chatOverlayRef.value
    if (!overlay) {
      return
    }
    overlay.scrollTop = overlay.scrollHeight
  })
}

let sessionId = ''
let websocket: WebSocket | null = null

let micContext: AudioContext | null = null
let micStream: MediaStream | null = null
let micSource: MediaStreamAudioSourceNode | null = null
let micProcessor: ScriptProcessorNode | null = null
let micMuteGain: GainNode | null = null
let micAnalyser: AnalyserNode | null = null
let micAnalyserBuffer: Uint8Array | null = null
let micSampleRate = 16000

let ttsContext: AudioContext | null = null
let ttsMasterGain: GainNode | null = null
let ttsAnalyser: AnalyserNode | null = null
let ttsAnalyserBuffer: Uint8Array | null = null
let activePlaybackSource: AudioBufferSourceNode | null = null
const playbackQueue: AudioPayload[] = []
let playbackDraining = false
let playbackGeneration = 0
let stoppedUtteranceId = 0

let visualizerFrameId = 0

const activeServerInput = (() => {
  const fromQuery = new URLSearchParams(window.location.search).get('server')
  if (fromQuery && fromQuery.trim()) {
    return fromQuery.trim()
  }
  const fromEnv = import.meta.env.VITE_MM_SERVER_URL
  if (fromEnv && fromEnv.trim()) {
    return fromEnv.trim()
  }
  if (import.meta.env.DEV) {
    return 'http://localhost:5000'
  }
  if (window.location.protocol === 'http:' || window.location.protocol === 'https:') {
    return window.location.origin
  }
  return 'http://localhost:5000'
})()

function updateStatus(next: string): void {
  statusText.value = next
}

function normalizeServerUrl(rawUrl: string): URL {
  const input = (rawUrl || '').trim()
  if (!input) {
    return new URL('http://localhost:5000')
  }
  if (/^[a-zA-Z][a-zA-Z\d+.-]*:\/\//.test(input)) {
    return new URL(input)
  }
  return new URL(`http://${input}`)
}

function toHttpBaseUrl(rawUrl: string): string {
  const url = normalizeServerUrl(rawUrl)
  if (url.protocol === 'ws:') {
    url.protocol = 'http:'
  } else if (url.protocol === 'wss:') {
    url.protocol = 'https:'
  }
  return url.origin
}

function toWsBaseUrl(rawUrl: string): string {
  const url = normalizeServerUrl(rawUrl)
  if (url.protocol === 'http:') {
    url.protocol = 'ws:'
  } else if (url.protocol === 'https:') {
    url.protocol = 'wss:'
  }
  return url.origin
}

async function createSession(serverInput: string): Promise<string> {
  const httpBase = toHttpBaseUrl(serverInput)
  const response = await fetch(`${httpBase}/sessions`, { method: 'POST' })
  if (!response.ok) {
    throw new Error(`セッション作成に失敗しました: HTTP ${response.status}`)
  }
  const payload = await response.json() as { session_id?: string }
  if (!payload.session_id) {
    throw new Error('セッションIDが返されませんでした')
  }
  return payload.session_id
}

async function openWebSocket(serverInput: string, createdSessionId: string): Promise<WebSocket> {
  const wsBase = toWsBaseUrl(serverInput)
  const wsUrl = `${wsBase}/dialogue/ws/${createdSessionId}`
  return await new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl)
    ws.onopen = () => resolve(ws)
    ws.onerror = () => reject(new Error('WebSocket接続に失敗しました'))
  })
}

function sendSocketMessage(payload: Record<string, unknown>): void {
  if (!websocket || websocket.readyState !== WebSocket.OPEN) {
    return
  }
  websocket.send(JSON.stringify(payload))
}

function downsampleTo16k(input: Float32Array, sourceRate: number): Float32Array {
  const targetRate = 16000
  if (sourceRate === targetRate) {
    return input
  }
  if (sourceRate < targetRate) {
    throw new Error(`Unsupported microphone sample rate: ${sourceRate}Hz`)
  }

  const ratio = sourceRate / targetRate
  const outLength = Math.floor(input.length / ratio)
  const output = new Float32Array(outLength)
  let outOffset = 0
  let inOffset = 0

  while (outOffset < outLength) {
    const nextInOffset = Math.round((outOffset + 1) * ratio)
    let sum = 0
    let count = 0
    for (let i = inOffset; i < nextInOffset && i < input.length; i += 1) {
      sum += input[i]
      count += 1
    }
    output[outOffset] = count > 0 ? sum / count : 0
    outOffset += 1
    inOffset = nextInOffset
  }

  return output
}

function float32ToBase64Pcm16(input: Float32Array): string {
  const pcm16 = new Int16Array(input.length)
  for (let i = 0; i < input.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, input[i]))
    pcm16[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff
  }

  const bytes = new Uint8Array(pcm16.buffer)
  let binary = ''
  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}

function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes.buffer
}

function enqueueAudio(payload: AudioPayload): void {
  playbackQueue.push(payload)
  void drainPlaybackQueue()
}

function stopPlayback(reason: string, utteranceId: number): void {
  playbackGeneration += 1
  stoppedUtteranceId = Math.max(stoppedUtteranceId, utteranceId)
  playbackQueue.length = 0
  if (activePlaybackSource) {
    activePlaybackSource.onended = null
    try {
      activePlaybackSource.stop()
    } catch {
      // no-op
    }
    activePlaybackSource.disconnect()
    activePlaybackSource = null
  }
  sendSocketMessage({
    action: 'stop_audio_done',
    reason,
    aux_data: AUX_DATA_DEBUG
  })
}

function calculateRmsFromByteWave(buffer: Uint8Array): number {
  let sum = 0
  for (let i = 0; i < buffer.length; i += 1) {
    const norm = (buffer[i] - 128) / 128
    sum += norm * norm
  }
  return Math.sqrt(sum / buffer.length)
}

async function drainPlaybackQueue(): Promise<void> {
  if (playbackDraining) {
    return
  }
  if (!ttsContext) {
    return
  }

  playbackDraining = true
  const currentGeneration = playbackGeneration

  try {
    if (ttsContext.state === 'suspended') {
      await ttsContext.resume()
    }

    while (playbackQueue.length > 0) {
      if (currentGeneration !== playbackGeneration) {
        break
      }

      const item = playbackQueue.shift()
      if (!item) {
        break
      }

      if (item.utteranceId <= stoppedUtteranceId) {
        continue
      }

      try {
        const wavBuffer = base64ToArrayBuffer(item.audio)
        const decodedBuffer = await ttsContext.decodeAudioData(wavBuffer.slice(0))
        if (currentGeneration !== playbackGeneration) {
          break
        }

        await new Promise<void>((resolve) => {
          if (!ttsContext) {
            resolve()
            return
          }

          const source = ttsContext.createBufferSource()
          activePlaybackSource = source
          source.buffer = decodedBuffer
          if (ttsMasterGain) {
            source.connect(ttsMasterGain)
          } else {
            source.connect(ttsContext.destination)
          }
          source.onended = () => {
            if (activePlaybackSource === source) {
              activePlaybackSource = null
            }
            source.disconnect()
            resolve()
          }
          source.start()
        })

        if (currentGeneration !== playbackGeneration) {
          break
        }

        sendSocketMessage({
          action: 'tts_segment_playback_done',
          utterance_id: item.utteranceId,
          segment_index: item.segmentIndex,
          segment_count: item.segmentCount,
          aux_data: AUX_DATA_DEBUG
        })
      } catch (error) {
        console.error('Audio playback failed', error)
      }
    }
  } finally {
    playbackDraining = false
  }
}

function setupSocketHandlers(ws: WebSocket): void {
  ws.onmessage = (event: MessageEvent<string>) => {
    const message = JSON.parse(event.data) as {
      event: string
      payload?: Record<string, unknown>
    }

    if (message.event === 'system_message') {
      const payload = message.payload || {}
      pushChatMessage('system', String(payload.text || ''))
      return
    }

    if (message.event === 'user_message') {
      const payload = message.payload || {}
      pushChatMessage('user', String(payload.text || ''))
      return
    }

    if (message.event === 'audio_data') {
      const payload = message.payload || {}
      enqueueAudio({
        audio: String(payload.audio || ''),
        utteranceId: Number(payload.utterance_id || 0),
        segmentIndex: Number(payload.segment_index || 0),
        segmentCount: Number(payload.segment_count || 0)
      })
      return
    }

    if (message.event === 'stop_audio') {
      const payload = message.payload || {}
      stopPlayback(String(payload.reason || 'cancel'), Number(payload.utterance_id || 0))
      return
    }

    if (message.event === 'error') {
      const payload = message.payload || {}
      errorText.value = String(payload.message || 'サーバエラーが発生しました')
      return
    }
  }

  ws.onclose = () => {
    websocket = null
    if (state.value === 'running' || state.value === 'starting') {
      state.value = 'error'
      updateStatus('接続が切断されました')
    }
  }

  ws.onerror = () => {
    if (state.value !== 'stopping') {
      state.value = 'error'
      updateStatus('通信エラー')
    }
  }
}

async function startMicrophone(): Promise<void> {
  if (!window.isSecureContext) {
    throw new Error('マイク利用には HTTPS または localhost が必要です')
  }

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    throw new Error('この環境ではマイクを利用できません')
  }

  const AudioContextCtor = window.AudioContext || (window as WebAudioWindow).webkitAudioContext
  if (!AudioContextCtor) {
    throw new Error('AudioContextが利用できません')
  }

  micContext = new AudioContextCtor()
  if (micContext.state === 'suspended') {
    await micContext.resume()
  }

  updateStatus('マイク許可待ち...')

  micSampleRate = micContext.sampleRate
  try {
    micStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      }
    })
  } catch {
    // Fallback for browsers/devices that do not accept detailed constraints.
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true })
  }

  micSource = micContext.createMediaStreamSource(micStream)
  micAnalyser = micContext.createAnalyser()
  micAnalyser.fftSize = 1024
  micAnalyser.smoothingTimeConstant = 0.72
  micAnalyserBuffer = new Uint8Array(micAnalyser.fftSize)

  micProcessor = micContext.createScriptProcessor(4096, 1, 1)
  micMuteGain = micContext.createGain()
  micMuteGain.gain.value = 0

  micProcessor.onaudioprocess = (event: AudioProcessingEvent) => {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) {
      return
    }
    const input = event.inputBuffer.getChannelData(0)
    const pcm16k = downsampleTo16k(input, micSampleRate)
    if (!pcm16k.length) {
      return
    }
    sendSocketMessage({
      action: 'send_audio_chunk',
      audio_data: float32ToBase64Pcm16(pcm16k),
      aux_data: AUX_DATA_DEBUG
    })
  }

  micSource.connect(micAnalyser)
  micSource.connect(micProcessor)
  micProcessor.connect(micMuteGain)
  micMuteGain.connect(micContext.destination)

  startVisualizerLoop()
}

function stopMicrophone(): void {
  if (visualizerFrameId) {
    cancelAnimationFrame(visualizerFrameId)
    visualizerFrameId = 0
  }

  if (micProcessor) {
    micProcessor.disconnect()
    micProcessor.onaudioprocess = null
    micProcessor = null
  }
  if (micMuteGain) {
    micMuteGain.disconnect()
    micMuteGain = null
  }
  if (micSource) {
    micSource.disconnect()
    micSource = null
  }
  if (micAnalyser) {
    micAnalyser.disconnect()
    micAnalyser = null
  }
  if (micStream) {
    micStream.getTracks().forEach((track) => track.stop())
    micStream = null
  }
  if (micContext) {
    void micContext.close()
    micContext = null
  }
  micAnalyserBuffer = null
  renderIdleWave()
}

function resizeCanvasForDpr(canvas: HTMLCanvasElement): CanvasRenderingContext2D | null {
  const rect = canvas.getBoundingClientRect()
  const dpr = window.devicePixelRatio || 1
  const width = Math.max(1, Math.floor(rect.width * dpr))
  const height = Math.max(1, Math.floor(rect.height * dpr))
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width
    canvas.height = height
  }
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    return null
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  return ctx
}

function drawWaveform(): void {
  const canvas = canvasRef.value
  if (!canvas) {
    return
  }
  const ctx = resizeCanvasForDpr(canvas)
  if (!ctx) {
    return
  }

  const width = canvas.clientWidth
  const height = canvas.clientHeight
  const centerY = height / 2

  ctx.clearRect(0, 0, width, height)
  ctx.strokeStyle = 'rgba(20, 32, 53, 0.25)'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(0, centerY)
  ctx.lineTo(width, centerY)
  ctx.stroke()

  const candidates: Array<{ buffer: Uint8Array, rms: number, source: 'mic' | 'tts' }> = []
  if (micAnalyser && micAnalyserBuffer) {
    micAnalyser.getByteTimeDomainData(micAnalyserBuffer)
    candidates.push({
      buffer: micAnalyserBuffer,
      rms: calculateRmsFromByteWave(micAnalyserBuffer),
      source: 'mic'
    })
  }
  if (ttsAnalyser && ttsAnalyserBuffer) {
    ttsAnalyser.getByteTimeDomainData(ttsAnalyserBuffer)
    candidates.push({
      buffer: ttsAnalyserBuffer,
      rms: calculateRmsFromByteWave(ttsAnalyserBuffer),
      source: 'tts'
    })
  }

  if (!candidates.length) {
    return
  }

  const weightedLevel = (candidate: { rms: number, source: 'mic' | 'tts' }): number => {
    if (candidate.source === 'mic') {
      return candidate.rms * MIC_VISUAL_BOOST
    }
    return candidate.rms * TTS_VISUAL_BOOST
  }

  let selected = candidates[0]
  for (let i = 1; i < candidates.length; i += 1) {
    if (weightedLevel(candidates[i]) > weightedLevel(selected)) {
      selected = candidates[i]
    }
  }

  const waveformBuffer = selected.buffer
  const amplitude = Math.min(1, Math.max(BASE_WAVE_FLOOR, weightedLevel(selected) * 18))

  const points = 72
  const maxHeight = Math.max(12, height * 0.42)
  const step = width / (points - 1)

  ctx.strokeStyle = 'rgba(20, 32, 53, 0.95)'
  ctx.lineWidth = 2.2
  ctx.beginPath()
  for (let i = 0; i < points; i += 1) {
    const dataIndex = Math.floor((i / points) * waveformBuffer.length)
    const normalized = (waveformBuffer[dataIndex] - 128) / 128
    const yOffset = normalized * maxHeight * amplitude
    const x = i * step
    const y = centerY - yOffset
    if (i === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  }
  ctx.stroke()

  ctx.strokeStyle = 'rgba(20, 32, 53, 0.5)'
  ctx.lineWidth = 1.4
  ctx.beginPath()
  for (let i = 0; i < points; i += 1) {
    const dataIndex = Math.floor((i / points) * waveformBuffer.length)
    const normalized = (waveformBuffer[dataIndex] - 128) / 128
    const yOffset = normalized * maxHeight * amplitude
    const x = i * step
    const y = centerY + yOffset
    if (i === 0) {
      ctx.moveTo(x, y)
    } else {
      ctx.lineTo(x, y)
    }
  }
  ctx.stroke()
}

function visualizerTick(): void {
  drawWaveform()
  visualizerFrameId = requestAnimationFrame(visualizerTick)
}

function startVisualizerLoop(): void {
  if (visualizerFrameId) {
    cancelAnimationFrame(visualizerFrameId)
    visualizerFrameId = 0
  }
  visualizerTick()
}

function renderIdleWave(): void {
  const canvas = canvasRef.value
  if (!canvas) {
    return
  }
  const ctx = resizeCanvasForDpr(canvas)
  if (!ctx) {
    return
  }
  const width = canvas.clientWidth
  const height = canvas.clientHeight
  const centerY = height / 2

  ctx.clearRect(0, 0, width, height)
  ctx.strokeStyle = 'rgba(20, 32, 53, 0.25)'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(0, centerY)
  ctx.lineTo(width, centerY)
  ctx.stroke()
}

async function preparePlaybackContext(): Promise<void> {
  if (ttsContext) {
    if (ttsContext.state === 'suspended') {
      await ttsContext.resume()
    }
    return
  }
  const AudioContextCtor = window.AudioContext || (window as WebAudioWindow).webkitAudioContext
  if (!AudioContextCtor) {
    throw new Error('AudioContextが利用できません')
  }
  ttsContext = new AudioContextCtor()
  if (ttsContext.state === 'suspended') {
    await ttsContext.resume()
  }

  ttsAnalyser = ttsContext.createAnalyser()
  ttsAnalyser.fftSize = 1024
  ttsAnalyser.smoothingTimeConstant = 0.68
  ttsAnalyserBuffer = new Uint8Array(ttsAnalyser.fftSize)

  ttsMasterGain = ttsContext.createGain()
  ttsMasterGain.gain.value = 1
  ttsMasterGain.connect(ttsAnalyser)
  ttsAnalyser.connect(ttsContext.destination)
}

async function startClient(): Promise<void> {
  state.value = 'starting'
  errorText.value = ''
  chatMessages.value = []
  updateStatus('接続中...')

  try {
    await preparePlaybackContext()
    sessionId = await createSession(activeServerInput)
    websocket = await openWebSocket(activeServerInput, sessionId)
    setupSocketHandlers(websocket)

    sendSocketMessage({ action: 'start_dialogue', aux_data: AUX_DATA_DEBUG })
    await startMicrophone()

    stoppedUtteranceId = 0
    state.value = 'running'
    updateStatus('接続中 / 音声送受信中')
  } catch (error) {
    const message = error instanceof Error ? error.message : '開始処理に失敗しました'
    errorText.value = message
    await stopClient(true)
    state.value = 'error'
    updateStatus('開始失敗')
  }
}

async function stopClient(skipServerCall = false): Promise<void> {
  if (state.value !== 'running' && state.value !== 'starting' && state.value !== 'error') {
    return
  }

  state.value = 'stopping'
  updateStatus('停止中...')

  stopMicrophone()
  stopPlayback('end_dialogue', Number.MAX_SAFE_INTEGER)

  if (!skipServerCall) {
    sendSocketMessage({ action: 'end_dialogue', aux_data: AUX_DATA_DEBUG })
  }

  if (websocket) {
    websocket.onclose = null
    websocket.close()
    websocket = null
  }

  if (sessionId && !skipServerCall) {
    try {
      const httpBase = toHttpBaseUrl(activeServerInput)
      await fetch(`${httpBase}/sessions/${sessionId}`, { method: 'DELETE' })
    } catch {
      // no-op
    }
  }

  sessionId = ''
  state.value = 'idle'
  updateStatus('待機中')
}

async function onMainButtonTap(): Promise<void> {
  if (isBusy.value) {
    return
  }
  if (isActive.value) {
    await stopClient(false)
    return
  }
  await startClient()
}

function onWindowResize(): void {
  if (isActive.value) {
    drawWaveform()
  } else {
    renderIdleWave()
  }
}

onMounted(() => {
  renderIdleWave()
  window.addEventListener('resize', onWindowResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onWindowResize)
  void stopClient(true)
  if (ttsAnalyser) {
    ttsAnalyser.disconnect()
    ttsAnalyser = null
  }
  if (ttsMasterGain) {
    ttsMasterGain.disconnect()
    ttsMasterGain = null
  }
  ttsAnalyserBuffer = null
  if (ttsContext) {
    void ttsContext.close()
    ttsContext = null
  }
})
</script>

<template>
  <main class="screen">
    <section class="panel">
      <h1 class="title">DialBB Mobile</h1>
      <p class="status">{{ statusText }}</p>

      <section class="voice-pill" aria-label="chat and waveform panel">
        <div ref="chatOverlayRef" class="chat-overlay" aria-label="chat transcript">
          <p v-if="chatMessages.length === 0" class="chat-empty">会話待機中...</p>
          <p v-for="(message, index) in chatMessages" :key="index" class="chat-line" :class="message.role">
            <span class="chat-text">{{ message.text }}</span>
          </p>
        </div>
        <canvas ref="canvasRef" class="wave-canvas" aria-label="voice waveform"></canvas>
      </section>

      <p v-if="errorText" class="error-text">{{ errorText }}</p>

      <button class="main-button" :class="{ active: isActive }" :disabled="isBusy" @click="onMainButtonTap">
        {{ buttonLabel }}
      </button>
    </section>
  </main>
</template>

<style scoped>
:global(html), :global(body), :global(#app) {
  margin: 0;
  width: 100%;
  min-height: 100%;
}

.screen {
  --ink: #11233b;
  --paper: #fffdf6;
  --accent: #e36a2d;
  --accent-deep: #c84f16;
  min-height: 100dvh;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle at 15% 20%, rgba(236, 187, 145, 0.6), transparent 45%),
    radial-gradient(circle at 82% 82%, rgba(177, 205, 229, 0.42), transparent 44%),
    linear-gradient(165deg, #fffdf6 0%, #fff5e8 47%, #fff 100%);
  padding: 14px;
  box-sizing: border-box;
}

.panel {
  width: min(420px, 96vw);
  min-height: min(82dvh, 700px);
  border-radius: 22px;
  border: 1px solid rgba(17, 35, 59, 0.16);
  background: rgba(255, 255, 255, 0.84);
  backdrop-filter: blur(8px);
  padding: 18px 14px 16px;
  box-shadow: 0 16px 44px rgba(17, 35, 59, 0.14);
  display: grid;
  align-content: center;
  gap: 8px;
}

.voice-pill {
  width: min(320px, 84vw);
  justify-self: center;
  margin-top: 2px;
  border-radius: 30px;
  border: 1px solid rgba(17, 35, 59, 0.2);
  background: linear-gradient(180deg, rgba(240, 248, 255, 0.8), rgba(255, 255, 255, 0.9));
  padding: 10px 10px 10px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
  display: grid;
  gap: 8px;
}

.chat-overlay {
  min-height: 280px;
  max-height: 360px;
  overflow-y: auto;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(17, 35, 59, 0.14);
  padding: 8px 10px;
  display: grid;
  gap: 6px;
}

.chat-empty {
  margin: 0;
  text-align: center;
  color: rgba(17, 35, 59, 0.58);
  font-size: 0.84rem;
  font-family: "Segoe UI", sans-serif;
}

.chat-line {
  margin: 0;
  border-radius: 10px;
  padding: 5px 8px;
}

.chat-line.user {
  background: rgba(30, 73, 102, 0.13);
}

.chat-line.system {
  background: rgba(227, 106, 45, 0.14);
}

.chat-text {
  font-size: 0.8rem;
  line-height: 1.3;
  color: rgba(17, 35, 59, 0.92);
  font-family: "Segoe UI", sans-serif;
  overflow-wrap: anywhere;
}

.title {
  margin: 0;
  text-align: center;
  color: var(--ink);
  font-family: "Trebuchet MS", "Segoe UI", sans-serif;
  letter-spacing: 0.03em;
  font-size: clamp(1.2rem, 3.8vw, 1.8rem);
}

.status {
  margin: 0;
  text-align: center;
  color: rgba(17, 35, 59, 0.8);
  font-family: "Segoe UI", sans-serif;
  font-size: 0.95rem;
}

.main-button {
  border: none;
  border-radius: 999px;
  padding: 10px 20px;
  justify-self: center;
  min-width: 122px;
  font-family: "Trebuchet MS", "Segoe UI", sans-serif;
  font-weight: 700;
  font-size: 0.94rem;
  letter-spacing: 0.04em;
  color: #fff;
  background: linear-gradient(150deg, var(--accent) 0%, var(--accent-deep) 100%);
  box-shadow: 0 10px 24px rgba(227, 106, 45, 0.33);
  transition: transform 150ms ease, box-shadow 150ms ease, filter 150ms ease;
}

.main-button.active {
  background: linear-gradient(150deg, #1e4966 0%, #173349 100%);
  box-shadow: 0 10px 24px rgba(23, 51, 73, 0.35);
}

.main-button:disabled {
  opacity: 0.68;
}

.main-button:not(:disabled):active {
  transform: translateY(1px) scale(0.996);
  filter: saturate(1.08);
}

.wave-canvas {
  width: 100%;
  height: clamp(54px, 12vw, 70px);
  border-radius: 999px;
  border: 1px solid rgba(17, 35, 59, 0.22);
  background: linear-gradient(180deg, rgba(232, 244, 255, 0.66), rgba(255, 255, 255, 0.92));
}

.error-text {
  margin: 0;
  color: #8f1d1d;
  text-align: center;
  font-family: "Segoe UI", sans-serif;
  font-size: 0.9rem;
}

@media (max-height: 760px) {
  .screen {
    place-items: start center;
    padding-top: 10px;
  }

  .panel {
    min-height: min(94dvh, 700px);
    align-content: start;
  }
}
</style>
