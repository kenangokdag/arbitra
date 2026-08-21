import { cleanup } from "@testing-library/react"
import { afterEach } from "vitest"

import "@testing-library/jest-dom/vitest"

// jsdom'un Blob'ı arrayBuffer() implement etmez (tarayıcıda vardır; TTS sesli-
// dinlet akışı AudioContext'e beslemek için kullanır). Gerçek davranışı veren
// FileReader ile polyfill — stub değil, asıl baytları döndürür.
if (
  typeof Blob !== "undefined" &&
  typeof Blob.prototype.arrayBuffer !== "function"
) {
  Blob.prototype.arrayBuffer = function arrayBuffer(): Promise<ArrayBuffer> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result as ArrayBuffer)
      reader.onerror = () => reject(reader.error)
      reader.readAsArrayBuffer(this)
    })
  }
}

afterEach(() => {
  cleanup()
})
