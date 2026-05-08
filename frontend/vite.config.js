import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/outputs': {
        target: 'http://localhost:3000',
        bypass(req, res) {
          // Serve files directly from C:\Evotrade\outputs\
          const filePath = path.join('C:/Evotrade/outputs', req.url.replace('/outputs', ''))
          if (fs.existsSync(filePath)) {
            res.setHeader('Content-Type', 'application/json')
            res.setHeader('Cache-Control', 'no-cache')
            res.end(fs.readFileSync(filePath, 'utf-8'))
            return false
          }
        },
      },
    },
  },
})
