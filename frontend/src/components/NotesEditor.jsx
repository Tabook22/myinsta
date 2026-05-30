import { useCallback, useEffect, useRef, useState } from 'react'
import { EditorContent, useEditor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Underline from '@tiptap/extension-underline'
import TextAlign from '@tiptap/extension-text-align'
import { TextStyle, FontSize } from '@tiptap/extension-text-style'
import Color from '@tiptap/extension-color'
import Highlight from '@tiptap/extension-highlight'
import Link from '@tiptap/extension-link'
import Image from '@tiptap/extension-image'
import { Table, TableRow, TableHeader, TableCell } from '@tiptap/extension-table'
import html2pdf from 'html2pdf.js'
import { updateVideo } from '../api/client.js'
import { useLanguage } from '../context/LanguageContext.jsx'

// ── Toolbar primitives ────────────────────────────────────────────────────────
function Btn({ onClick, active, title, disabled, children }) {
  return (
    <button
      type="button"
      className={`rte-btn${active ? ' rte-btn-active' : ''}`}
      onClick={onClick}
      title={title}
      disabled={disabled}
    >
      {children}
    </button>
  )
}

function Sep() { return <span className="rte-sep" /> }

// ── Component ─────────────────────────────────────────────────────────────────
export default function NotesEditor({ video }) {
  const { t } = useLanguage()
  const [saveStatus, setSaveStatus]   = useState('idle') // idle | saving | saved | error
  const [pdfGenerating, setPdfGenerating] = useState(false)
  const saveTimer   = useRef(null)
  const statusTimer = useRef(null)
  const imageInput  = useRef(null)
  const editorRef   = useRef(null)

  // Debounced auto-save (1 second after last keystroke)
  const saveNotes = useCallback(async (html) => {
    setSaveStatus('saving')
    try {
      await updateVideo(video.id, { notes: html })
      setSaveStatus('saved')
      clearTimeout(statusTimer.current)
      statusTimer.current = setTimeout(() => setSaveStatus('idle'), 2500)
    } catch {
      setSaveStatus('error')
    }
  }, [video.id])

  const editor = useEditor({
    extensions: [
      StarterKit.configure({ heading: { levels: [1, 2, 3, 4] } }),
      Underline,
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      TextStyle,
      FontSize,
      Color,
      Highlight.configure({ multicolor: true }),
      Link.configure({ openOnClick: false, autolink: true }),
      Image.configure({ inline: false, allowBase64: true }),
      Table.configure({ resizable: true }),
      TableRow,
      TableHeader,
      TableCell,
    ],
    content: video.notes || '',
    onUpdate({ editor }) {
      clearTimeout(saveTimer.current)
      setSaveStatus('idle')
      saveTimer.current = setTimeout(() => saveNotes(editor.getHTML()), 1000)
    },
  })

  // Reload content when switching to a different video
  useEffect(() => {
    if (!editor) return
    const incoming = video.notes || ''
    if (editor.getHTML() !== incoming) {
      editor.commands.setContent(incoming, false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [video.id])

  // Cleanup timers on unmount
  useEffect(() => () => {
    clearTimeout(saveTimer.current)
    clearTimeout(statusTimer.current)
  }, [])

  // ── Toolbar helpers ─────────────────────────────────────────────────────────
  const insertLink = useCallback(() => {
    if (!editor) return
    const prev = editor.getAttributes('link').href || ''
    const url  = window.prompt(t('enterUrl'), prev || 'https://')
    if (url === null) return           // cancelled
    if (url === '') {
      editor.chain().focus().unsetLink().run()
    } else {
      editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run()
    }
  }, [editor])

  const handleImageFile = useCallback((e) => {
    const file = e.target.files[0]
    if (!file || !editor) return
    const reader = new FileReader()
    reader.onload = () =>
      editor.chain().focus().setImage({ src: reader.result, alt: file.name }).run()
    reader.readAsDataURL(file)
    e.target.value = ''
  }, [editor])

  const insertTable = useCallback(() => {
    editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()
  }, [editor])

  const setHeading = useCallback((e) => {
    const v = Number(e.target.value)
    if (v === 0) editor.chain().focus().setParagraph().run()
    else         editor.chain().focus().setHeading({ level: v }).run()
  }, [editor])

  const setFontSize = useCallback((e) => {
    const v = e.target.value
    if (!v) editor.chain().focus().unsetFontSize().run()
    else    editor.chain().focus().setFontSize(v).run()
  }, [editor])

  const downloadAsPdf = useCallback(async () => {
    if (!editor || pdfGenerating) return
    setPdfGenerating(true)

    // Build a styled wrapper so the PDF looks clean
    const title   = video.title || t('untitledVideo')
    const filename = t('notesPdfFilename', title.replace(/[/\\:*?"<>|]/g, '-'))
    const isRtl    = document.documentElement.dir === 'rtl'

    const wrapper = document.createElement('div')
    wrapper.style.cssText = [
      'font-family: "Segoe UI", Arial, sans-serif',
      'font-size: 14px',
      'line-height: 1.7',
      'color: #1e293b',
      'padding: 8px',
      `direction: ${isRtl ? 'rtl' : 'ltr'}`,
      `text-align: ${isRtl ? 'right' : 'left'}`,
    ].join(';')

    // Title heading
    const heading = document.createElement('h1')
    heading.style.cssText = 'font-size:20px;margin:0 0 4px;color:#0f172a;border-bottom:2px solid #e2e8f0;padding-bottom:6px'
    heading.textContent = title

    // Subtitle (date)
    const sub = document.createElement('p')
    sub.style.cssText = 'font-size:11px;color:#94a3b8;margin:0 0 16px'
    sub.textContent = new Date().toLocaleDateString(isRtl ? 'ar-SA' : 'en-US', {
      year: 'numeric', month: 'long', day: 'numeric',
    })

    // Notes body — clone the rendered ProseMirror content
    const body = document.createElement('div')
    body.innerHTML = editor.getHTML()

    wrapper.appendChild(heading)
    wrapper.appendChild(sub)
    wrapper.appendChild(body)

    // Temporarily attach to DOM so html2pdf can measure it
    wrapper.style.position = 'absolute'
    wrapper.style.left = '-9999px'
    document.body.appendChild(wrapper)

    try {
      await html2pdf().set({
        margin:      [12, 14, 12, 14],   // top, right, bottom, left (mm)
        filename,
        image:       { type: 'jpeg', quality: 0.97 },
        html2canvas: { scale: 2, useCORS: true, logging: false },
        jsPDF:       { unit: 'mm', format: 'a4', orientation: 'portrait' },
        pagebreak:   { mode: ['avoid-all', 'css'] },
      }).from(wrapper).save()
    } finally {
      document.body.removeChild(wrapper)
      setPdfGenerating(false)
    }
  }, [editor, pdfGenerating, video.title, t])

  if (!editor) return null

  const curHeading = [1,2,3,4].find(l => editor.isActive('heading', { level: l })) ?? 0
  const inTable    = editor.isActive('table')

  return (
    <div className="notes-editor-wrap">

      {/* ── Header ── */}
      <div className="notes-editor-header">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
        </svg>
        <span>{t('myNotes')}</span>
        <span className={`notes-save-badge notes-save-${saveStatus}`}>
          {saveStatus === 'saving' && t('noteSaving')}
          {saveStatus === 'saved'  && t('noteSaved')}
          {saveStatus === 'error'  && t('noteSaveFailed')}
        </span>

        <button
          type="button"
          className="notes-pdf-btn"
          onClick={downloadAsPdf}
          disabled={pdfGenerating}
          title={t('downloadNotesPdf')}
        >
          {pdfGenerating ? t('notesPdfGenerating') : (
            <>
              {/* Download icon */}
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              {t('downloadNotesPdfShort')}
            </>
          )}
        </button>
      </div>

      {/* ── Toolbar ── */}
      <div className="rte-toolbar">

        {/* History */}
        <Btn onClick={() => editor.chain().focus().undo().run()}
          disabled={!editor.can().undo()} title={t('undo')}>↩</Btn>
        <Btn onClick={() => editor.chain().focus().redo().run()}
          disabled={!editor.can().redo()} title={t('redo')}>↪</Btn>
        <Sep />

        {/* Heading style */}
        <select className="rte-select" value={curHeading} onChange={setHeading} title={t('headingNormal')}>
          <option value={0}>{t('headingNormal')}</option>
          <option value={1}>{t('heading1')}</option>
          <option value={2}>{t('heading2')}</option>
          <option value={3}>{t('heading3')}</option>
          <option value={4}>{t('heading4')}</option>
        </select>

        {/* Font size */}
        <select className="rte-select rte-select-sm" onChange={setFontSize} defaultValue="" title={t('fontSize')}>
          <option value="">{t('fontSize')}</option>
          {['11px','12px','14px','16px','18px','20px','24px','28px','32px','40px','48px'].map(s =>
            <option key={s} value={s}>{s.replace('px','')}</option>
          )}
        </select>
        <Sep />

        {/* Text format */}
        <Btn onClick={() => editor.chain().focus().toggleBold().run()}
          active={editor.isActive('bold')} title={t('bold')}><b>B</b></Btn>
        <Btn onClick={() => editor.chain().focus().toggleItalic().run()}
          active={editor.isActive('italic')} title={t('italic')}><i>I</i></Btn>
        <Btn onClick={() => editor.chain().focus().toggleUnderline().run()}
          active={editor.isActive('underline')} title={t('underline')}><u>U</u></Btn>
        <Btn onClick={() => editor.chain().focus().toggleStrike().run()}
          active={editor.isActive('strike')} title={t('strikethrough')}><s>S</s></Btn>
        <Sep />

        {/* Colors */}
        <label className="rte-color-btn" title={t('textColor')}>
          <span className="rte-color-label">A</span>
          <input type="color" defaultValue="#000000"
            onChange={e => editor.chain().focus().setColor(e.target.value).run()} />
        </label>
        <label className="rte-color-btn rte-highlight-btn" title={t('highlightColor')}>
          <span className="rte-color-label">H</span>
          <input type="color" defaultValue="#fef08a"
            onChange={e => editor.chain().focus().setHighlight({ color: e.target.value }).run()} />
        </label>
        <Sep />

        {/* Alignment */}
        <Btn onClick={() => editor.chain().focus().setTextAlign('left').run()}
          active={editor.isActive({ textAlign: 'left' })} title={t('alignLeft')}>⬅</Btn>
        <Btn onClick={() => editor.chain().focus().setTextAlign('center').run()}
          active={editor.isActive({ textAlign: 'center' })} title={t('alignCenter')}>⬛</Btn>
        <Btn onClick={() => editor.chain().focus().setTextAlign('right').run()}
          active={editor.isActive({ textAlign: 'right' })} title={t('alignRight')}>➡</Btn>
        <Btn onClick={() => editor.chain().focus().setTextAlign('justify').run()}
          active={editor.isActive({ textAlign: 'justify' })} title={t('justify')}>≡</Btn>
        <Sep />

        {/* Lists */}
        <Btn onClick={() => editor.chain().focus().toggleBulletList().run()}
          active={editor.isActive('bulletList')} title={t('bulletList')}>•≡</Btn>
        <Btn onClick={() => editor.chain().focus().toggleOrderedList().run()}
          active={editor.isActive('orderedList')} title={t('orderedList')}>1≡</Btn>
        <Sep />

        {/* Insert */}
        <Btn onClick={insertLink} active={editor.isActive('link')} title={t('insertLink')}>🔗</Btn>
        <Btn onClick={() => imageInput.current?.click()} title={t('uploadImage')}>🖼</Btn>
        <Btn onClick={insertTable} title={t('insertTable')}>⊞</Btn>
        <input ref={imageInput} type="file" accept="image/*"
          style={{ display: 'none' }} onChange={handleImageFile} />

        {/* Contextual table controls (visible only when cursor is inside a table) */}
        {inTable && (
          <>
            <Sep />
            <Btn onClick={() => editor.chain().focus().addColumnAfter().run()} title={t('addColAfter')}>+col</Btn>
            <Btn onClick={() => editor.chain().focus().addRowAfter().run()} title={t('addRowAfter')}>+row</Btn>
            <Btn onClick={() => editor.chain().focus().deleteColumn().run()} title={t('deleteCol')}>−col</Btn>
            <Btn onClick={() => editor.chain().focus().deleteRow().run()} title={t('deleteRow')}>−row</Btn>
            <Btn onClick={() => editor.chain().focus().deleteTable().run()} title={t('deleteTable')}>🗑</Btn>
          </>
        )}
      </div>

      {/* ── Editor content area ── */}
      <EditorContent editor={editor} className="rte-body" />
    </div>
  )
}
