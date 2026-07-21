const { contextBridge, ipcRenderer, webUtils } = require('electron')
const pu = require('./platform-utils')

contextBridge.exposeInMainWorld('earpipe', {
  transcribe: (filePath, engine, title) => ipcRenderer.invoke('transcribe', filePath, engine, title),
  openFileDialog: () => ipcRenderer.invoke('open-file-dialog'),
  saveFile: (src, ext, name) => ipcRenderer.invoke('save-file', src, ext, name),
  openExternal: (filePath) => ipcRenderer.invoke('open-external', filePath),
  getPathForFile: (file) => webUtils.getPathForFile(file),
  // 3.3/3.4: クロスプラットフォームなbasenameとfile URL符号化をrenderer側へ公開
  basenameForDisplay: (filePath) => pu.basenameForDisplay(filePath),
  filePathToUrl: (filePath) => pu.filePathToUrl(filePath),
  onProgress: (cb) => {
    const handler = (_, msg) => cb(msg)
    ipcRenderer.on('transcribe-progress', handler)
    return () => ipcRenderer.removeListener('transcribe-progress', handler)
  },
})
