const { contextBridge, ipcRenderer, webUtils } = require('electron')

contextBridge.exposeInMainWorld('earpipe', {
  transcribe: (filePath, engine) => ipcRenderer.invoke('transcribe', filePath, engine),
  openFileDialog: () => ipcRenderer.invoke('open-file-dialog'),
  saveFile: (src, ext, name) => ipcRenderer.invoke('save-file', src, ext, name),
  openExternal: (filePath) => ipcRenderer.invoke('open-external', filePath),
  getPathForFile: (file) => webUtils.getPathForFile(file),
  onProgress: (cb) => {
    const handler = (_, msg) => cb(msg)
    ipcRenderer.on('transcribe-progress', handler)
    return () => ipcRenderer.removeListener('transcribe-progress', handler)
  },
})
