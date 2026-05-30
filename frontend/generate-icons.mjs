/**
 * Generates solid-color PNG icons for the PWA manifest.
 * Run once: node generate-icons.mjs
 * Uses only built-in Node.js modules — no npm install needed.
 */
import { deflateSync } from 'zlib'
import { writeFileSync, mkdirSync } from 'fs'

function crc32(buf) {
  let crc = 0xFFFFFFFF
  for (const b of buf) {
    crc ^= b
    for (let i = 0; i < 8; i++)
      crc = (crc & 1) ? (crc >>> 1) ^ 0xEDB88320 : (crc >>> 1)
  }
  return (crc ^ 0xFFFFFFFF) >>> 0
}

function u32be(n) {
  const b = Buffer.alloc(4)
  b.writeUInt32BE(n, 0)
  return b
}

function pngChunk(type, data) {
  const t = Buffer.from(type, 'ascii')
  return Buffer.concat([u32be(data.length), t, data, u32be(crc32(Buffer.concat([t, data])))])
}

function solidPng(size, r, g, b) {
  const ihdr = Buffer.alloc(13)
  ihdr.writeUInt32BE(size, 0)
  ihdr.writeUInt32BE(size, 4)
  ihdr[8] = 8; ihdr[9] = 2  // 8-bit RGB

  // Each row: [filter=0, r, g, b, r, g, b, ...]
  const row = Buffer.alloc(1 + size * 3)
  row[0] = 0
  for (let x = 0; x < size; x++) {
    row[1 + x * 3] = r
    row[2 + x * 3] = g
    row[3 + x * 3] = b
  }
  const raw = Buffer.concat(Array.from({ length: size }, () => row))

  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]), // PNG sig
    pngChunk('IHDR', ihdr),
    pngChunk('IDAT', deflateSync(raw)),
    pngChunk('IEND', Buffer.alloc(0)),
  ])
}

mkdirSync('public/icons', { recursive: true })
// Indigo #4f46e5 = rgb(79, 70, 229)
writeFileSync('public/icons/icon-192.png', solidPng(192, 79, 70, 229))
writeFileSync('public/icons/icon-512.png', solidPng(512, 79, 70, 229))
writeFileSync('public/icons/icon-180.png', solidPng(180, 79, 70, 229)) // Apple touch icon
console.log('✅ Icons generated in public/icons/')
