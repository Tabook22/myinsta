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
import { updateVideo } from '../api/client.js'

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
  const [saveStatus, setSaveStatus]   = useState('idle') // idle | saving | saved | error
  const saveTimer   = useRef(null)
  const statusTimer = useRef(null)
  const imageInput  = useRef(null)

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
    const url  = window.prompt('Enter URL:', prev || 'https://')
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
        <span>My Notes</span>
        <span className={`notes-save-badge notes-save-${saveStatus}`}>
          {saveStatus === 'saving' && '⏳ Saving…'}
          {saveStatus === 'saved'  && '✓ Saved'}
          {saveStatus === 'error'  && '⚠ Save failed — retry'}
        </span>
      </div>

      {/* ── Toolbar ── */}
      <div className="rte-toolbar">

        {/* History */}
        <Btn onClick={() => editor.chain().focus().undo().run()}
          disabled={!editor.can().undo()} title="Undo">↩</Btn>
        <Btn onClick={() => editor.chain().focus().redo().run()}
          disabled={!editor.can().redo()} title="Redo">↪</Btn>
        <Sep />

        {/* Heading style */}
        <select className="rte-select" value={curHeading} onChange={setHeading} title="Heading style">
          <option value={0}>Normal</option>
          <option value={1}>Heading 1</option>
          <option value={2}>Heading 2</option>
          <option value={3}>Heading 3</option>
          <option value={4}>Heading 4</option>
        </select>

        {/* Font size */}
        <select className="rte-select rte-select-sm" onChange={setFontSize} defaultValue="" title="Font size">
          <option value="">Size</option>
          {['11px','12px','14px','16px','18px','20px','24px','28px','32px','40px','48px'].map(s =>
            <option key={s} value={s}>{s.replace('px','')}</option>
          )}
        </select>
        <Sep />

        {/* Text format */}
        <Btn onClick={() => editor.chain().focus().toggleBold().run()}
          active={editor.isActive('bold')} title="Bold"><b>B</b></Btn>
        <Btn onClick={() => editor.chain().focus().toggleItalic().run()}
          active={editor.isActive('italic')} title="Italic"><i>I</i></Btn>
        <Btn onClick={() => editor.chain().focus().toggleUnderline().run()}
          active={editor.isActive('underline')} title="Underline"><u>U</u></Btn>
        <Btn onClick={() => editor.chain().focus().toggleStrike().run()}
          active={editor.isActive('strike')} title="Strikethrough"><s>S</s></Btn>
        <Sep />

        {/* Colors */}
        <label className="rte-color-btn" title="Text color">
          <span className="rte-color-label">A</span>
          <input type="color" defaultValue="#000000"
            onChange={e => editor.chain().focus().setColor(e.target.value).run()} />
        </label>
        <label className="rte-color-btn rte-highlight-btn" title="Highlight / background color">
          <span className="rte-color-label">H</span>
          <input type="color" defaultValue="#fef08a"
            onChange={e => editor.chain().focus().setHighlight({ color: e.target.value }).run()} />
        </label>
        <Sep />

        {/* Alignment */}
        <Btn onClick={() => editor.chain().focus().setTextAlign('left').run()}
          active={editor.isActive({ textAlign: 'left' })} title="Align left">⬅</Btn>
        <Btn onClick={() => editor.chain().focus().setTextAlign('center').run()}
          active={editor.isActive({ textAlign: 'center' })} title="Center">⬛</Btn>
        <Btn onClick={() => editor.chain().focus().setTextAlign('right').run()}
          active={editor.isActive({ textAlign: 'right' })} title="Align right">➡</Btn>
        <Btn onClick={() => editor.chain().focus().setTextAlign('justify').run()}
          active={editor.isActive({ textAlign: 'justify' })} title="Justify">≡</Btn>
        <Sep />

        {/* Lists */}
        <Btn onClick={() => editor.chain().focus().toggleBulletList().run()}
          active={editor.isActive('bulletList')} title="Bullet list">•≡</Btn>
        <Btn onClick={() => editor.chain().focus().toggleOrderedList().run()}
          active={editor.isActive('orderedList')} title="Ordered list">1≡</Btn>
        <Sep />

        {/* Insert */}
        <Btn onClick={insertLink} active={editor.isActive('link')} title="Insert / edit link">🔗</Btn>
        <Btn onClick={() => imageInput.current?.click()} title="Upload image from your device">🖼</Btn>
        <Btn onClick={insertTable} title="Insert 3×3 table">⊞</Btn>
        <input ref={imageInput} type="file" accept="image/*"
          style={{ display: 'none' }} onChange={handleImageFile} />

        {/* Contextual table controls (visible only when cursor is inside a table) */}
        {inTable && (
          <>
            <Sep />
            <Btn onClick={() => editor.chain().focus().addColumnAfter().run()} title="Add column after">+col</Btn>
            <Btn onClick={() => editor.chain().focus().addRowAfter().run()} title="Add row after">+row</Btn>
            <Btn onClick={() => editor.chain().focus().deleteColumn().run()} title="Delete column">−col</Btn>
            <Btn onClick={() => editor.chain().focus().deleteRow().run()} title="Delete row">−row</Btn>
            <Btn onClick={() => editor.chain().focus().deleteTable().run()} title="Delete table">🗑</Btn>
          </>
        )}
      </div>

      {/* ── Editor content area ── */}
      <EditorContent editor={editor} className="rte-body" />
    </div>
  )
}
