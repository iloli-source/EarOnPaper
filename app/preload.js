const { contextBridge, ipcRenderer, webUtils } = require('electron')

// sandbox:true 下の preload はローカルモジュールを require できないため、
// レンダラへ渡す純粋ヘルパはここへインライン化する(platform-utils と同一実装)。
// PDF の file URL は node:url が要るため preload では作らず、メイン側が結果に pdfUrl を付す。
function basenameForDisplay(filePath) {
  if (typeof filePath !== 'string') return ''
  const parts = filePath.split(/[\\/]/)
  return parts[parts.length - 1] || ''
}

// 保存初期名の曲名スネーク化(platform-utils.snakeFileStem と同一実装・上記の理由でインライン)
function snakeFileStem(title, max = 80) {
  if (typeof title !== 'string') return 'score'
  const snaked = title
    .replace(/[\s/\\:*?"<>|()[\]{}'!&,;#~^$%+=@`-]+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^[_.]+|[_.]+$/g, '')
    .toLowerCase()
    .slice(0, max)
  return snaked || 'score'
}

function exportFileName(title, stemId, kind, ext) {
  const parts = [snakeFileStem(title)]
  if (stemId) parts.push(String(stemId))
  if (kind) parts.push(String(kind))
  return `${parts.join('_')}.${String(ext).replace(/^\./, '')}`
}

contextBridge.exposeInMainWorld('earpipe', {
  transcribe: (filePath, engine, title, progressToken) =>
    ipcRenderer.invoke('transcribe', filePath, engine, title, progressToken),
  // 分離→選択楽器のみ採譜フロー
  separateAudio: (filePath, progressToken) =>
    ipcRenderer.invoke('separate-audio', filePath, progressToken),
  transcribeStem: (filePath, stemId, title, opts, progressToken) =>
    ipcRenderer.invoke('transcribe-stem', filePath, stemId, title, opts, progressToken),
  releaseInput: (filePath) => ipcRenderer.invoke('release-input', filePath),
  cancelOperation: (token) => ipcRenderer.invoke('cancel-operation', token),
  openFileDialog: () => ipcRenderer.invoke('open-file-dialog'),
  // #128: URL取り込み(yt-dlpローカル実行)。成功で { path, title } を返す
  importUrl: (url, progressToken) => ipcRenderer.invoke('import-url', url, progressToken),
  saveFile: (src, ext, name) => ipcRenderer.invoke('save-file', src, ext, name),
  // 詳細エクスポート(簡譜/度数/GP5等)。savePath は E2E 時のみ使用。
  exportExtra: (inputPath, key, e2eSavePath, defaultName) =>
    ipcRenderer.invoke('export-extra', inputPath, key, e2eSavePath, defaultName),
  openExternal: (filePath) => ipcRenderer.invoke('open-external', filePath),
  getPathForFile: (file) => webUtils.getPathForFile(file),
  // 3.3: クロスプラットフォームな basename を renderer 側へ公開(純粋・sandbox安全)
  basenameForDisplay: (filePath) => basenameForDisplay(filePath),
  // 保存初期名: 曲名_楽器_種別.拡張子(スネークケース・2026-07-24要望)
  exportFileName: (title, stemId, kind, ext) => exportFileName(title, stemId, kind, ext),
  onProgress: (cb) => {
    const handler = (_, payload) => cb(payload)
    ipcRenderer.on('transcribe-progress', handler)
    return () => ipcRenderer.removeListener('transcribe-progress', handler)
  },
})
