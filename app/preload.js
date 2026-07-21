const { contextBridge, ipcRenderer, webUtils } = require('electron')

// sandbox:true 下の preload はローカルモジュールを require できないため、
// レンダラへ渡す純粋ヘルパはここへインライン化する(platform-utils と同一実装)。
// PDF の file URL は node:url が要るため preload では作らず、メイン側が結果に pdfUrl を付す。
function basenameForDisplay(filePath) {
  if (typeof filePath !== 'string') return ''
  const parts = filePath.split(/[\\/]/)
  return parts[parts.length - 1] || ''
}

contextBridge.exposeInMainWorld('earpipe', {
  transcribe: (filePath, engine, title) => ipcRenderer.invoke('transcribe', filePath, engine, title),
  openFileDialog: () => ipcRenderer.invoke('open-file-dialog'),
  saveFile: (src, ext, name) => ipcRenderer.invoke('save-file', src, ext, name),
  openExternal: (filePath) => ipcRenderer.invoke('open-external', filePath),
  getPathForFile: (file) => webUtils.getPathForFile(file),
  // 3.3: クロスプラットフォームな basename を renderer 側へ公開(純粋・sandbox安全)
  basenameForDisplay: (filePath) => basenameForDisplay(filePath),
  onProgress: (cb) => {
    const handler = (_, msg) => cb(msg)
    ipcRenderer.on('transcribe-progress', handler)
    return () => ipcRenderer.removeListener('transcribe-progress', handler)
  },
})
