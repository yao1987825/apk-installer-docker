<template>
  <div class="container">
    <div class="card">
      <h1>📱 APK 安装器</h1>
      <p class="subtitle">通过 Web 界面向设备安装应用</p>
      
      <div :class="['status-card', deviceConnected ? 'status-connected' : 'status-disconnected']">
        <div class="status-info">
          <div class="status-dot"></div>
          <span>{{ deviceConnected ? '设备已连接' : '设备未连接' }}</span>
        </div>
        <div class="device-info" v-if="deviceConnected">
          {{ deviceIp }} · {{ deviceAbi }}
        </div>
      </div>
      
      <div 
        class="upload-area" 
        @click="$refs.fileInput.click()"
        @dragover.prevent="dragOver = true"
        @dragleave="dragOver = false"
        @drop.prevent="handleDrop"
        :class="{ dragover: dragOver }"
      >
        <div class="upload-icon">📦</div>
        <div class="upload-text">点击或拖拽 APK 文件到此处</div>
        <div class="upload-hint">仅支持 .apk 格式</div>
        <input 
          type="file" 
          ref="fileInput"
          accept=".apk" 
          @change="handleFileSelect"
          style="display: none"
        >
      </div>
      
      <div class="file-selected" v-if="selectedFile">
        <div class="file-info">
          <div class="file-name">{{ selectedFile.name }}</div>
          <div class="file-size">{{ formatFileSize(selectedFile.size) }}</div>
        </div>
        <button class="btn-reselect" @click="reselectFile">重新选择</button>
      </div>
      
      <button 
        class="btn btn-primary" 
        @click="installApk"
        :disabled="!selectedFile || isInstalling"
      >
        {{ isInstalling ? '安装中...' : '开始安装' }}
      </button>
    </div>
    
    <div class="card installing-animation" :class="{ 'status-success': installStatus === 'success', 'status-error': installStatus === 'error' }" v-if="isInstalling">
      <div class="subway-map">
        <div class="station" :class="{ active: currentStage === '连接', completed: ['上传','安装','校验','完成'].includes(currentStage) }">
          <div class="station-dot"></div>
          <div class="station-label">连接</div>
        </div>
        <div class="line" :class="{ active: ['上传','安装','校验','完成'].includes(currentStage) }"></div>
        <div class="station" :class="{ active: currentStage === '上传', completed: ['安装','校验','完成'].includes(currentStage) }">
          <div class="station-dot"></div>
          <div class="station-label">上传</div>
        </div>
        <div class="line" :class="{ active: ['安装','校验','完成'].includes(currentStage) }"></div>
        <div class="station" :class="{ active: currentStage === '安装', completed: ['校验','完成'].includes(currentStage) }">
          <div class="station-dot"></div>
          <div class="station-label">安装</div>
        </div>
        <div class="line" :class="{ active: ['校验','完成'].includes(currentStage) }"></div>
        <div class="station" :class="{ active: currentStage === '校验', completed: currentStage === '完成' }">
          <div class="station-dot"></div>
          <div class="station-label">校验</div>
        </div>
        <div class="line" :class="{ active: currentStage === '完成' }"></div>
        <div class="station" :class="{ active: currentStage === '完成' }">
          <div class="station-dot"></div>
          <div class="station-label">完成</div>
        </div>
      </div>
    </div>
    
    <div class="card result" :class="installSuccess ? 'result-success' : 'result-error'" v-if="installStatus === 'success' || installStatus === 'error'">
      <div class="result-title">{{ installSuccess ? '安装成功' : '安装失败' }}</div>
      <div class="result-message">{{ resultMessage }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const deviceIp = ref('-')
const deviceConnected = ref(false)
const deviceAbi = ref('')
const selectedFile = ref(null)
const isInstalling = ref(false)
const dragOver = ref(false)
const showResult = ref(false)
const installSuccess = ref(false)
const resultMessage = ref('')

const currentStage = ref('等待')
const installStatus = ref('idle') // idle, success, error
const progress = ref(0)
const installId = ref(null)
let progressEventSource = null

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

const checkStatus = async () => {
  try {
    const res = await fetch('/device/status')
    const data = await res.json()
    deviceIp.value = data.device_ip || '-'
    deviceConnected.value = data.connected
    deviceAbi.value = data.device_abi || ''
  } catch (e) {
    console.error('Status check failed:', e)
  }
}

const handleFileSelect = (e) => {
  const file = e.target.files[0]
  if (file && file.name.endsWith('.apk')) {
    selectedFile.value = file
    showResult.value = false
  }
  e.target.value = ''
}

const handleDrop = (e) => {
  dragOver.value = false
  const file = e.dataTransfer.files[0]
  if (file && file.name.endsWith('.apk')) {
    selectedFile.value = file
    showResult.value = false
  }
}

const reselectFile = () => {
  selectedFile.value = null
  showResult.value = false
}

const getStageFromPercentage = (pct) => {
  if (pct >= 90) return '完成'
  if (pct >= 80) return '校验'
  if (pct >= 50) return '安装'
  if (pct > 0) return '上传'
  return '等待'
}

const startProgressPolling = (installId) => {
  if (progressEventSource) {
    progressEventSource.close()
  }
  
  progressEventSource = new EventSource(`/progress/${installId}`)
  
  progressEventSource.onmessage = (event) => {
    const data = event.data
    if (data === 'waiting') return
    
    const parts = data.split('|')
    const percentage = parseInt(parts[1]) || 0
    
    progress.value = percentage
    currentStage.value = getStageFromPercentage(percentage)
    saveInstallState()
    
    if (percentage >= 100) {
      installStatus.value = 'success'
      setTimeout(() => {
        if (progressEventSource) {
          progressEventSource.close()
          progressEventSource = null
        }
        showInstallResult()
      }, 3000)
    } else if (percentage < 0) {
      installStatus.value = 'error'
      if (progressEventSource) {
        progressEventSource.close()
        progressEventSource = null
      }
      showInstallResult()
    }
  }
  
  progressEventSource.onerror = () => {
    if (progressEventSource) {
      progressEventSource.close()
      progressEventSource = null
    }
    if (installStatus.value !== 'success' && installStatus.value !== 'error') {
      setTimeout(() => {
        if (installId.value) {
          startProgressPolling(installId.value)
        }
      }, 2000)
    }
  }
}

const showInstallResult = () => {
  isInstalling.value = false
  currentStage.value = '完成'
  
  if (installStatus.value === 'success') {
    installSuccess.value = true
    resultMessage.value = 'APK已成功安装到设备'
  } else {
    installSuccess.value = false
    resultMessage.value = '安装失败，请重试'
  }
  
  setTimeout(() => {
    currentStage.value = '等待'
    installStatus.value = 'idle'
    installSuccess.value = false
    resultMessage.value = ''
    
    localStorage.removeItem('apkInstallState')
  }, 5000)
}

const saveInstallState = () => {
  localStorage.setItem('apkInstallState', JSON.stringify({
    isInstalling: isInstalling.value,
    currentStage: currentStage.value,
    installStatus: installStatus.value,
    fileName: selectedFile.value ? selectedFile.value.name : null,
    progress: progress.value,
    installId: installId.value
  }))
}

const loadInstallState = () => {
  const saved = localStorage.getItem('apkInstallState')
  if (saved) {
    try {
      const state = JSON.parse(saved)
      if (state.isInstalling && state.currentStage && state.currentStage !== '等待' && state.currentStage !== '完成') {
        isInstalling.value = true
        currentStage.value = state.currentStage
        installStatus.value = state.installStatus || 'idle'
        progress.value = state.progress || 0
        if (state.fileName) {
          selectedFile.value = { name: state.fileName }
        }
        if (state.installId && state.currentStage !== '完成') {
          installId.value = state.installId
          startProgressPolling(state.installId)
        }
      }
    } catch (e) {
      localStorage.removeItem('apkInstallState')
    }
  }
}

const installApk = async () => {
  if (!selectedFile.value || isInstalling.value) return
  
  isInstalling.value = true
  showResult.value = false
  currentStage.value = '上传'
  installStatus.value = 'idle'
  
  saveInstallState()
  
  const fileToUpload = selectedFile.value
  
  const formData = new FormData()
  formData.append('file', fileToUpload)
  
  try {
    const uploadResult = await new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          currentStage.value = '上传'
        }
      })
      
      xhr.addEventListener('load', () => {
        try {
          const data = JSON.parse(xhr.responseText)
          resolve(data)
        } catch (e) {
          reject(new Error('Invalid response'))
        }
      })
      
      xhr.addEventListener('error', () => reject(new Error('Upload failed')))
      
      xhr.open('POST', '/upload')
      xhr.send(formData)
    })
    
    if (!uploadResult.install_id) {
      throw new Error('Upload failed')
    }
    
    installId.value = uploadResult.install_id
    currentStage.value = '安装'
    saveInstallState()
    
    startProgressPolling(uploadResult.install_id)
    
    await new Promise(r => setTimeout(r, 500))
    
    const installRes = await fetch('/start-install', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        install_id: uploadResult.install_id, 
        apk_path: uploadResult.apk_path 
      })
    })
    
    await installRes.json()
    
  } catch (e) {
    isInstalling.value = false
    currentStage.value = '等待'
  }
}

onMounted(() => {
  checkStatus()
  setInterval(checkStatus, 5000)
  loadInstallState()
})

onUnmounted(() => {
  if (progressEventSource) {
    progressEventSource.close()
  }
})
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { 
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
  min-height: 100vh; 
  padding: 20px; 
}
.container { max-width: 600px; margin: 0 auto; }
.card { background: white; border-radius: 16px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); padding: 30px; margin-bottom: 20px; }
h1 { text-align: center; color: #333; margin-bottom: 10px; font-size: 28px; }
.subtitle { text-align: center; color: #666; margin-bottom: 30px; }
.status-card { display: flex; align-items: center; justify-content: space-between; padding: 15px 20px; border-radius: 12px; margin-bottom: 20px; }
.status-connected { background: #d4edda; border: 1px solid #c3e6cb; }
.status-disconnected { background: #f8d7da; border: 1px solid #f5c6cb; }
.status-info { display: flex; align-items: center; gap: 10px; }
.status-dot { width: 12px; height: 12px; border-radius: 50%; background: #dc3545; }
.status-connected .status-dot { background: #28a745; }
.upload-area { border: 2px dashed #ddd; border-radius: 12px; padding: 40px 20px; text-align: center; cursor: pointer; transition: all 0.3s; position: relative; }
.upload-area:hover { border-color: #667eea; background: #f8f9ff; }
.upload-area.dragover { border-color: #667eea; background: #f0f3ff; }
.upload-icon { font-size: 48px; margin-bottom: 15px; }
.upload-text { color: #666; margin-bottom: 10px; }
.upload-hint { color: #999; font-size: 12px; }
.file-selected { margin-top: 15px; padding: 15px; background: #e7f3ff; border-radius: 8px; display: flex; align-items: center; justify-content: space-between; }
.file-info { flex: 1; }
.file-name { color: #333; font-weight: 500; word-break: break-all; margin-bottom: 5px; }
.file-size { color: #666; font-size: 14px; }
.btn-reselect { padding: 8px 16px; background: #fff; border: 1px solid #667eea; border-radius: 6px; color: #667eea; cursor: pointer; font-size: 14px; }
.btn-reselect:hover { background: #667eea; color: white; }
.btn { width: 100%; padding: 15px; border: none; border-radius: 12px; font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.3s; margin-top: 20px; }
.btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
.btn-primary:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.result { padding: 20px; border-radius: 12px; display: block; }
.result-success { background: #d4edda; border: 1px solid #c3e6cb; }
.result-error { background: #f8d7da; border: 1px solid #f5c6cb; }
.result-title { font-weight: 600; margin-bottom: 10px; font-size: 18px; }
.result-success .result-title { color: #155724; }
.result-error .result-title { color: #721c24; }
.result-message { color: #333; line-height: 1.6; }
.installing-animation.status-success .station-dot, .installing-animation.status-success .line, .installing-animation.status-success .station.active .station-dot { background: #28a745 !important; border-color: #28a745 !important; box-shadow: 0 0 0 4px rgba(40, 167, 69, 0.3) !important; }
.installing-animation.status-success .station-label, .installing-animation.status-success .station.active .station-label { color: #28a745 !important; }
.installing-animation.status-success .station.completed .station-dot, .installing-animation.status-success .station.completed .station-label { background: #28a745 !important; color: #28a745 !important; }
.installing-animation.status-error .station-dot, .installing-animation.status-error .line, .installing-animation.status-error .station.active .station-dot { background: #dc3545 !important; border-color: #dc3545 !important; box-shadow: 0 0 0 4px rgba(220, 53, 69, 0.3) !important; }
.installing-animation.status-error .station-label, .installing-animation.status-error .station.active .station-label { color: #dc3545 !important; }
.installing-animation.status-error .station.completed .station-dot, .installing-animation.status-error .station.completed .station-label { background: #dc3545 !important; color: #dc3545 !important; }
.spinner { width: 50px; height: 50px; border: 4px solid #f3f3f3; border-top: 4px solid #667eea; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 15px; }
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
.subway-map { display: flex; align-items: center; justify-content: center; margin-bottom: 20px; padding: 10px 0; }
.station { display: flex; flex-direction: column; align-items: center; z-index: 1; }
.station-dot { width: 20px; height: 20px; border-radius: 50%; background: #e0e0e0; border: 3px solid #fff; box-shadow: 0 2px 4px rgba(0,0,0,0.1); transition: all 0.3s; }
.station.active .station-dot { background: #667eea; transform: scale(1.3); box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.3); }
.station.completed .station-dot { background: #28a745; }
.station-label { font-size: 12px; color: #999; margin-top: 8px; font-weight: 500; }
.station.active .station-label { color: #667eea; font-weight: 600; }
.station.completed .station-label { color: #28a745; }
.line { width: 40px; height: 4px; background: #e0e0e0; margin: 0 -2px; z-index: 0; transition: background 0.3s; }
.line.active { background: #667eea; }
.installing-animation { display: none; text-align: center; padding: 30px; }
.installing-animation { display: block; }
.progress-container { margin-top: 20px; }
.progress-bar { height: 8px; background: #e9ecef; border-radius: 4px; overflow: hidden; margin-top: 15px; }
.progress-fill { height: 100%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); width: 0%; transition: width 0.3s; }
.installing-status { font-size: 16px; color: #333; margin-bottom: 10px; }
.progress-percentage { font-size: 24px; font-weight: bold; color: #667eea; margin-top: 10px; }
.device-info { font-size: 14px; color: #666; }
</style>
