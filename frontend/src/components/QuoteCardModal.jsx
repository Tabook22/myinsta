import { useEffect, useRef } from 'react'
import { useLanguage } from '../context/LanguageContext.jsx'

// ── Canvas helpers ────────────────────────────────────────────────────────────
function isRTL(text) { return /[؀-ۿ]/.test(text) }

function wrapText(ctx, text, maxWidth) {
  const words = text.split(' ')
  const lines = []
  let line = words[0] || ''
  for (let i = 1; i < words.length; i++) {
    const test = line + ' ' + words[i]
    if (ctx.measureText(test).width <= maxWidth) { line = test }
    else { lines.push(line); line = words[i] }
  }
  lines.push(line)
  return lines
}

function getOptimalSize(ctx, text, maxW, maxH) {
  for (let size = 62; size >= 24; size -= 4) {
    ctx.font = `500 ${size}px system-ui,-apple-system,sans-serif`
    const lines = wrapText(ctx, text, maxW)
    if (lines.length <= 7 && lines.length * size * 1.55 <= maxH) return size
  }
  return 24
}

function drawCard(canvas, quote, creator, title) {
  const W = 1080, H = 1080
  canvas.width  = W
  canvas.height = H
  const ctx = canvas.getContext('2d')
  const rtl = isRTL(quote)

  // ── Background gradient ──
  const bg = ctx.createLinearGradient(0, 0, W, H)
  bg.addColorStop(0, '#0f172a')
  bg.addColorStop(1, '#1e1b4b')
  ctx.fillStyle = bg
  ctx.fillRect(0, 0, W, H)

  // ── Subtle noise texture overlay ──
  ctx.fillStyle = 'rgba(255,255,255,0.015)'
  for (let i = 0; i < 4000; i++) {
    ctx.fillRect(Math.random() * W, Math.random() * H, 1, 1)
  }

  // ── Left accent bar ──
  const barX = rtl ? W - 66 : 60
  const barGrad = ctx.createLinearGradient(0, 140, 0, 880)
  barGrad.addColorStop(0, '#4f46e5')
  barGrad.addColorStop(1, '#7c3aed')
  ctx.fillStyle = barGrad
  ctx.beginPath()
  ctx.roundRect(barX, 140, 7, 760, 4)
  ctx.fill()

  // ── Decorative quote mark ──
  ctx.fillStyle = 'rgba(99,102,241,0.18)'
  ctx.font = 'bold 220px Georgia,serif'
  ctx.textAlign = rtl ? 'right' : 'left'
  ctx.fillText('"', rtl ? W - 85 : 85, 320)

  // ── Quote text ──
  const textX   = rtl ? W - 110 : 110
  const textY   = 280
  const textMaxW = W - 220
  const textMaxH = 520

  const fontSize = getOptimalSize(ctx, quote, textMaxW, textMaxH)
  ctx.font      = `500 ${fontSize}px system-ui,-apple-system,sans-serif`
  ctx.fillStyle = '#f1f5f9'
  ctx.textAlign = rtl ? 'right' : 'left'
  ctx.direction = rtl ? 'rtl' : 'ltr'

  const lines    = wrapText(ctx, quote, textMaxW)
  const lineH    = fontSize * 1.55
  lines.forEach((line, i) => ctx.fillText(line, textX, textY + i * lineH))

  // ── Separator ──
  const sepY = textY + lines.length * lineH + 44
  const sepGrad = ctx.createLinearGradient(rtl ? W - 110 : 110, 0, rtl ? W - 510 : 510, 0)
  sepGrad.addColorStop(0, 'rgba(99,102,241,0.8)')
  sepGrad.addColorStop(1, 'rgba(99,102,241,0)')
  ctx.strokeStyle = sepGrad
  ctx.lineWidth   = 2
  ctx.beginPath()
  ctx.moveTo(rtl ? W - 110 : 110, sepY)
  ctx.lineTo(rtl ? W - 510 : 510, sepY)
  ctx.stroke()

  // ── Creator ──
  ctx.font      = `bold 40px system-ui,-apple-system,sans-serif`
  ctx.fillStyle = '#818cf8'
  ctx.fillText(creator ? `@${creator}` : '', textX, sepY + 58)

  // ── Video title ──
  if (title) {
    ctx.font      = `32px system-ui,-apple-system,sans-serif`
    ctx.fillStyle = 'rgba(148,163,184,0.65)'
    const short   = title.length > 48 ? title.slice(0, 48) + '…' : title
    ctx.fillText(short, textX, sepY + 108)
  }

  // ── Branding ──
  ctx.font      = '26px system-ui,-apple-system,sans-serif'
  ctx.fillStyle = 'rgba(148,163,184,0.38)'
  ctx.textAlign = rtl ? 'left' : 'right'
  ctx.direction = 'ltr'
  ctx.fillText('MyInsta', rtl ? 80 : W - 54, H - 42)
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function QuoteCardModal({ quote, video, onClose }) {
  const { t } = useLanguage()
  const canvasRef = useRef(null)

  useEffect(() => {
    if (canvasRef.current) {
      drawCard(canvasRef.current, quote, video.uploader || '', video.title || '')
    }
  }, [quote, video])

  function handleDownload() {
    const a = document.createElement('a')
    a.href     = canvasRef.current.toDataURL('image/png')
    a.download = `quote-${Date.now()}.png`
    a.click()
  }

  return (
    <div className="quote-backdrop" onClick={onClose}>
      <div className="quote-modal" onClick={(e) => e.stopPropagation()}>
        <div className="quote-modal-header">
          <h2>{t('quoteCardTitle')}</h2>
          <button type="button" className="shortcuts-close" onClick={onClose}>✕</button>
        </div>

        <div className="quote-canvas-wrap">
          <canvas ref={canvasRef} className="quote-canvas" />
        </div>

        <div className="quote-modal-actions">
          <button type="button" className="quote-download-btn" onClick={handleDownload}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            {t('quoteDownloadPng')}
          </button>
          <p className="quote-hint">{t('quoteHint')}</p>
        </div>
      </div>
    </div>
  )
}
