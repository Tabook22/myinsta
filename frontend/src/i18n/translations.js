/**
 * UI string translations — English (en) and Arabic (ar).
 * Keys that take parameters are functions: (param) => string
 */

export const translations = {
  en: {
    // ── App ──────────────────────────────────────────────────────────────────
    appName: 'MyInsta',
    appSubtitle: 'Paste an Instagram video link, save it to your library, transcribe it, then chat with the transcript.',
    langLabel: 'Language',

    // ── Backend / connection ─────────────────────────────────────────────────
    backendOffline: '⚠️ Backend offline:',
    retry: 'Retry',
    connectingToServer: 'Connecting to server…',

    // ── URL form ─────────────────────────────────────────────────────────────
    urlPlaceholder: 'https://www.instagram.com/reel/...',
    processVideo: 'Process video',
    submitting: 'Submitting...',

    // ── Video library ────────────────────────────────────────────────────────
    yourVideos: 'Your Instagram videos',
    librarySubtitle: 'View, edit, or delete any saved video from your library.',
    noVideos: 'No saved videos yet. Paste an Instagram link above to get started.',
    colTitle: 'Title',
    colSavedAs: 'Saved as',
    colStatus: 'Status',
    colDate: 'Date',
    colActions: 'Actions',
    view: 'View',
    edit: 'Edit',
    delete: 'Delete',
    deleteConfirm: (label) => `Delete "${label}" and all saved files?`,
    videoHash: (id) => `Video #${id}`,
    openOnInstagram: (name) => `Open ${name} on Instagram`,
    creator: 'creator',

    // ── Video details ────────────────────────────────────────────────────────
    untitledVideo: 'Untitled video',
    labelSavedAs: 'Saved as:',
    labelFolder: 'Folder:',
    labelSource: 'Source:',
    labelCreator: 'Creator:',
    labelDuration: 'Duration:',
    labelDescription: 'Description:',
    openOriginal: 'Open original',
    seconds: 'seconds',
    editThisVideo: 'Edit this video',

    // ── Transcript ───────────────────────────────────────────────────────────
    transcript: 'Transcript',
    transcriptProcessing: 'Processing… transcript will appear when the video is ready.',
    noSpeech: 'No speech detected in this video.',

    // ── Video editor ─────────────────────────────────────────────────────────
    editSavedVideo: 'Edit saved video',
    deleting: 'Deleting…',
    saving: 'Saving…',
    saveChanges: 'Save changes',
    fieldTitle: 'Title',
    fieldDescription: 'Description',
    fieldTranscript: 'Transcript',

    // ── Chat panel ───────────────────────────────────────────────────────────
    chatWithVideo: 'Chat with video',
    modeTranscript: '🎯 Transcript',
    modeWeb: '🌐 Web',
    titleTranscript: 'Answer questions using the video transcript',
    titleWeb: 'Search the web to answer your question',
    noticeMusicWarning: '⚠️ This video appears to be music only — transcript may be empty.',
    switchToWeb: 'Switch to Web mode',
    noticeTranscriptReady: '🎯 Answering from the saved transcript.',
    noticeNoTranscript: '⚠️ No transcript found — answers may be limited.',
    noticeWebMode: '🌐 Searching the web using the video title and your question.',
    loadingConversation: 'Loading conversation...',
    chatPlaceholderWeb: 'Ask anything — results come from the web based on the video title.',
    chatPlaceholderTranscript: 'Ask something like "What is this video about?" or "What topics are covered?"',
    chatLocked: 'Chat unlocks after the video finishes processing.',
    you: 'You',
    inputPlaceholderWeb: 'Ask anything about this video or topic...',
    inputPlaceholderTranscript: 'Ask about the transcript...',
    inputPlaceholderLocked: 'Chat is available after transcription finishes',
    searching: 'Searching...',
    ask: 'Ask',

    // ── Audio player ─────────────────────────────────────────────────────────
    audioTrack: 'Audio track',
    downloadAudioTitle: 'Download audio file',
    download: 'Download',
    audioBrowserFallback: 'Your browser does not support audio playback.',

    // ── Notes editor ─────────────────────────────────────────────────────────
    myNotes: 'My Notes',
    noteSaving: '⏳ Saving…',
    noteSaved: '✓ Saved',
    noteSaveFailed: '⚠ Save failed — retry',
    notePlaceholder: 'Write your notes here…',
    enterUrl: 'Enter URL:',
    undo: 'Undo',
    redo: 'Redo',
    headingNormal: 'Normal',
    heading1: 'Heading 1',
    heading2: 'Heading 2',
    heading3: 'Heading 3',
    heading4: 'Heading 4',
    fontSize: 'Size',
    bold: 'Bold',
    italic: 'Italic',
    underline: 'Underline',
    strikethrough: 'Strikethrough',
    textColor: 'Text color',
    highlightColor: 'Highlight / background color',
    alignLeft: 'Align left',
    alignCenter: 'Center',
    alignRight: 'Align right',
    justify: 'Justify',
    bulletList: 'Bullet list',
    orderedList: 'Ordered list',
    insertLink: 'Insert / edit link',
    uploadImage: 'Upload image from your device',
    insertTable: 'Insert 3×3 table',
    addColAfter: 'Add column after',
    addRowAfter: 'Add row after',
    deleteCol: 'Delete column',
    deleteRow: 'Delete row',
    deleteTable: 'Delete table',
    downloadNotesPdf: 'Download notes as PDF',
    downloadNotesPdfShort: 'PDF',
    notesPdfFilename: (title) => `notes-${title || 'untitled'}.pdf`,
    notesPdfGenerating: 'Generating PDF…',
    notesSaveShortcut: 'Ctrl+S to save immediately',

    // ── Theme ────────────────────────────────────────────────────────────────
    switchToDark: 'Switch to dark mode',
    switchToLight: 'Switch to light mode',

    // ── Transcript actions ────────────────────────────────────────────────────
    copyTranscript: 'Copy transcript',
    transcriptCopied: '✓ Copied!',

    // ── Tags ─────────────────────────────────────────────────────────────────
    fieldTags: 'Tags',
    tagPlaceholder: 'Add tag and press Enter…',
    filterAll: 'All',
    noTagsYet: 'No tags yet',

    // ── Stats panel ───────────────────────────────────────────────────────────
    statsVideos: 'Videos',
    statsTranscribed: 'Transcribed',
    statsHours: 'hrs transcribed',
    statsChats: 'Questions asked',

    // ── Onboarding ────────────────────────────────────────────────────────────
    onboardingTitle: 'Welcome to MyInsta!',
    onboardingSubtitle: 'Your personal Instagram video library. Here\'s how it works:',
    onboardingStep1Title: 'Paste any Instagram link',
    onboardingStep1Desc: 'Drop a reel or video URL into the box — we download it automatically.',
    onboardingStep2Title: 'AI transcribes it for you',
    onboardingStep2Desc: 'Whisper AI extracts the audio and turns it into a searchable transcript.',
    onboardingStep3Title: 'Chat, notes & insights',
    onboardingStep3Desc: 'Ask questions, take rich notes, download PDFs — all in one place.',
    onboardingGetStarted: 'Get started →',

    // ── Notification ─────────────────────────────────────────────────────────
    notificationReady: (title) => `✅ "${title}" is ready!`,
    notificationBody: 'Your video has been transcribed. You can now chat with it.',

    // ── Library pagination & export ───────────────────────────────────────────
    loadMore: 'Load more',
    loadingMore: 'Loading…',
    allLoaded: (n) => `All ${n} videos loaded`,
    exportCsv: 'Export CSV',
    exportCsvTitle: 'Download your library as a spreadsheet',

    // ── Processing steps ─────────────────────────────────────────────────────
    stepDownloading:  'Downloading video',
    stepExtracting:   'Extracting audio',
    stepTranscribing: 'Transcribing',

    // ── Creator card ──────────────────────────────────────────────────────────
    creatorVideoCount: (n) => `${n} video${n === 1 ? '' : 's'} saved from this creator`,

    // ── Keyboard shortcuts ────────────────────────────────────────────────────
    shortcutsTitle:   'Keyboard Shortcuts',
    shortcutsTip:     'Press ? anytime to show this panel',
    shortcutHelp:     'Show keyboard shortcuts',
    shortcutSaveNotes:'Save notes immediately',
    shortcutSendChat: 'Send chat message',
    shortcutEscape:   'Close editor / close this panel',
    shortcutUndo:     'Undo (in notes editor)',
    shortcutRedo:     'Redo (in notes editor)',

    // ── Library view & sort ───────────────────────────────────────────────────
    viewList: 'List',
    viewGrid: 'Grid',
    sortLabel: 'Sort',
    sortNewest: 'Newest first',
    sortOldest: 'Oldest first',
    sortDuration: 'Longest first',
    sortTitleAZ: 'Title A–Z',
    sortTitleZA: 'Title Z–A',

    // ── Batch operations ──────────────────────────────────────────────────────
    selectAll: 'Select all',
    deselectAll: 'Deselect all',
    selectedCount: (n) => `${n} selected`,
    batchDelete: 'Move to trash',
    batchAddTag: '+ Tag',
    batchTagApply: 'Apply',
    batchDeleteConfirm: (n) => `Move ${n} video${n === 1 ? '' : 's'} to trash?`,

    // ── Trash ─────────────────────────────────────────────────────────────────
    trash: 'Trash',
    trashEmpty: 'Trash is empty',
    trashNotice: 'Items are permanently deleted after 30 days',
    trashDaysLeft: (n) => `${n}d left`,
    restore: 'Restore',
    deleteForever: 'Delete forever',
    deleteForeverConfirm: 'Delete forever? This cannot be undone.',
    emptyTrash: 'Empty trash',
    emptyTrashConfirm: 'Permanently delete all items in trash?',
  },

  ar: {
    // ── App ──────────────────────────────────────────────────────────────────
    appName: 'ماي إنستا',
    appSubtitle: 'الصق رابط فيديو إنستاجرام، احفظه في مكتبتك، استخرج نصه، ثم تحدث معه.',
    langLabel: 'اللغة',

    // ── Backend / connection ─────────────────────────────────────────────────
    backendOffline: '⚠️ الخادم غير متصل:',
    retry: 'إعادة المحاولة',
    connectingToServer: 'جارٍ الاتصال بالخادم…',

    // ── URL form ─────────────────────────────────────────────────────────────
    urlPlaceholder: 'https://www.instagram.com/reel/...',
    processVideo: 'معالجة الفيديو',
    submitting: 'جارٍ الإرسال...',

    // ── Video library ────────────────────────────────────────────────────────
    yourVideos: 'مقاطع الفيديو الخاصة بك',
    librarySubtitle: 'اعرض أو عدّل أو احذف أي فيديو محفوظ من مكتبتك.',
    noVideos: 'لا توجد مقاطع فيديو بعد. الصق رابط إنستاجرام أعلاه للبدء.',
    colTitle: 'العنوان',
    colSavedAs: 'محفوظ كـ',
    colStatus: 'الحالة',
    colDate: 'التاريخ',
    colActions: 'الإجراءات',
    view: 'عرض',
    edit: 'تعديل',
    delete: 'حذف',
    deleteConfirm: (label) => `هل تريد حذف "${label}" وجميع الملفات المحفوظة؟`,
    videoHash: (id) => `فيديو #${id}`,
    openOnInstagram: (name) => `فتح ${name} على إنستاجرام`,
    creator: 'المبدع',

    // ── Video details ────────────────────────────────────────────────────────
    untitledVideo: 'فيديو بلا عنوان',
    labelSavedAs: 'محفوظ كـ:',
    labelFolder: 'المجلد:',
    labelSource: 'المصدر:',
    labelCreator: 'المبدع:',
    labelDuration: 'المدة:',
    labelDescription: 'الوصف:',
    openOriginal: 'فتح الأصل',
    seconds: 'ثانية',
    editThisVideo: 'تعديل هذا الفيديو',

    // ── Transcript ───────────────────────────────────────────────────────────
    transcript: 'النص المكتوب',
    transcriptProcessing: 'جارٍ المعالجة… سيظهر النص عندما يكون الفيديو جاهزاً.',
    noSpeech: 'لم يتم اكتشاف كلام في هذا الفيديو.',

    // ── Video editor ─────────────────────────────────────────────────────────
    editSavedVideo: 'تعديل الفيديو المحفوظ',
    deleting: 'جارٍ الحذف…',
    saving: 'جارٍ الحفظ…',
    saveChanges: 'حفظ التغييرات',
    fieldTitle: 'العنوان',
    fieldDescription: 'الوصف',
    fieldTranscript: 'النص المكتوب',

    // ── Chat panel ───────────────────────────────────────────────────────────
    chatWithVideo: 'الدردشة مع الفيديو',
    modeTranscript: '🎯 النص',
    modeWeb: '🌐 الويب',
    titleTranscript: 'الإجابة بناءً على نص الفيديو',
    titleWeb: 'البحث في الويب للإجابة على سؤالك',
    noticeMusicWarning: '⚠️ يبدو أن هذا الفيديو موسيقى فقط — قد يكون النص فارغاً.',
    switchToWeb: 'التبديل إلى وضع الويب',
    noticeTranscriptReady: '🎯 الإجابة من النص المحفوظ.',
    noticeNoTranscript: '⚠️ لم يُعثر على نص — قد تكون الإجابات محدودة.',
    noticeWebMode: '🌐 البحث في الويب باستخدام عنوان الفيديو وسؤالك.',
    loadingConversation: 'جارٍ تحميل المحادثة...',
    chatPlaceholderWeb: 'اسأل أي شيء — ستأتي النتائج من الويب بناءً على عنوان الفيديو.',
    chatPlaceholderTranscript: 'اسأل مثلاً: "ما موضوع هذا الفيديو؟" أو "ما المواضيع التي تناولها؟"',
    chatLocked: 'ستُفتح الدردشة بعد اكتمال معالجة الفيديو.',
    you: 'أنت',
    inputPlaceholderWeb: 'اسأل أي شيء عن هذا الفيديو أو الموضوع...',
    inputPlaceholderTranscript: 'اسأل عن محتوى النص...',
    inputPlaceholderLocked: 'الدردشة متاحة بعد اكتمال النسخ',
    searching: 'جارٍ البحث...',
    ask: 'اسأل',

    // ── Audio player ─────────────────────────────────────────────────────────
    audioTrack: 'المقطع الصوتي',
    downloadAudioTitle: 'تحميل الملف الصوتي',
    download: 'تحميل',
    audioBrowserFallback: 'متصفحك لا يدعم تشغيل الصوت.',

    // ── Notes editor ─────────────────────────────────────────────────────────
    myNotes: 'ملاحظاتي',
    noteSaving: '⏳ جارٍ الحفظ…',
    noteSaved: '✓ تم الحفظ',
    noteSaveFailed: '⚠ فشل الحفظ — أعد المحاولة',
    notePlaceholder: 'اكتب ملاحظاتك هنا…',
    enterUrl: 'أدخل الرابط:',
    undo: 'تراجع',
    redo: 'إعادة',
    headingNormal: 'عادي',
    heading1: 'عنوان 1',
    heading2: 'عنوان 2',
    heading3: 'عنوان 3',
    heading4: 'عنوان 4',
    fontSize: 'الحجم',
    bold: 'عريض',
    italic: 'مائل',
    underline: 'تحته خط',
    strikethrough: 'يتوسطه خط',
    textColor: 'لون النص',
    highlightColor: 'لون التمييز',
    alignLeft: 'محاذاة لليسار',
    alignCenter: 'توسيط',
    alignRight: 'محاذاة لليمين',
    justify: 'ضبط',
    bulletList: 'قائمة نقطية',
    orderedList: 'قائمة مرقمة',
    insertLink: 'إدراج / تعديل رابط',
    uploadImage: 'رفع صورة من جهازك',
    insertTable: 'إدراج جدول 3×3',
    addColAfter: 'إضافة عمود بعد',
    addRowAfter: 'إضافة صف بعد',
    deleteCol: 'حذف عمود',
    deleteRow: 'حذف صف',
    deleteTable: 'حذف الجدول',
    downloadNotesPdf: 'تحميل الملاحظات كـ PDF',
    downloadNotesPdfShort: 'PDF',
    notesPdfFilename: (title) => `ملاحظات-${title || 'بلا-عنوان'}.pdf`,
    notesPdfGenerating: 'جارٍ إنشاء PDF…',
    notesSaveShortcut: 'Ctrl+S للحفظ الفوري',

    // ── Theme ────────────────────────────────────────────────────────────────
    switchToDark: 'التبديل إلى الوضع الداكن',
    switchToLight: 'التبديل إلى الوضع الفاتح',

    // ── Transcript actions ────────────────────────────────────────────────────
    copyTranscript: 'نسخ النص',
    transcriptCopied: '✓ تم النسخ!',

    // ── Tags ─────────────────────────────────────────────────────────────────
    fieldTags: 'الوسوم',
    tagPlaceholder: 'أضف وسمًا واضغط Enter…',
    filterAll: 'الكل',
    noTagsYet: 'لا توجد وسوم بعد',

    // ── Stats panel ───────────────────────────────────────────────────────────
    statsVideos: 'مقطع فيديو',
    statsTranscribed: 'جاهز',
    statsHours: 'ساعة منسوخة',
    statsChats: 'سؤال مطروح',

    // ── Onboarding ────────────────────────────────────────────────────────────
    onboardingTitle: 'مرحباً بك في ماي إنستا!',
    onboardingSubtitle: 'مكتبتك الشخصية لمقاطع إنستاجرام. إليك كيفية عملها:',
    onboardingStep1Title: 'الصق أي رابط إنستاجرام',
    onboardingStep1Desc: 'أسقط رابط مقطع أو فيديو في الصندوق — سنحمّله تلقائياً.',
    onboardingStep2Title: 'الذكاء الاصطناعي ينسخه لك',
    onboardingStep2Desc: 'يستخرج Whisper الصوت ويحوّله إلى نص قابل للبحث.',
    onboardingStep3Title: 'دردشة وملاحظات ورؤى',
    onboardingStep3Desc: 'اطرح أسئلة، خذ ملاحظات غنية، وحمّل PDF — كل ذلك في مكان واحد.',
    onboardingGetStarted: 'ابدأ الآن ←',

    // ── Notification ─────────────────────────────────────────────────────────
    notificationReady: (title) => `✅ "${title}" جاهز!`,
    notificationBody: 'تم نسخ الفيديو الخاص بك. يمكنك الآن التحدث معه.',

    // ── Library pagination & export ───────────────────────────────────────────
    loadMore: 'تحميل المزيد',
    loadingMore: 'جارٍ التحميل…',
    allLoaded: (n) => `تم تحميل جميع ${n} مقاطع`,
    exportCsv: 'تصدير CSV',
    exportCsvTitle: 'تحميل مكتبتك كجدول بيانات',

    // ── Processing steps ─────────────────────────────────────────────────────
    stepDownloading:  'تحميل الفيديو',
    stepExtracting:   'استخراج الصوت',
    stepTranscribing: 'النسخ إلى نص',

    // ── Creator card ──────────────────────────────────────────────────────────
    creatorVideoCount: (n) => `${n} فيديو محفوظ من هذا المبدع`,

    // ── Keyboard shortcuts ────────────────────────────────────────────────────
    shortcutsTitle:   'اختصارات لوحة المفاتيح',
    shortcutsTip:     'اضغط ? في أي وقت لعرض هذه اللوحة',
    shortcutHelp:     'عرض اختصارات لوحة المفاتيح',
    shortcutSaveNotes:'حفظ الملاحظات فوراً',
    shortcutSendChat: 'إرسال رسالة الدردشة',
    shortcutEscape:   'إغلاق المحرر / إغلاق هذه اللوحة',
    shortcutUndo:     'تراجع (في محرر الملاحظات)',
    shortcutRedo:     'إعادة (في محرر الملاحظات)',

    // ── Library view & sort ───────────────────────────────────────────────────
    viewList: 'قائمة',
    viewGrid: 'شبكة',
    sortLabel: 'ترتيب',
    sortNewest: 'الأحدث أولاً',
    sortOldest: 'الأقدم أولاً',
    sortDuration: 'الأطول أولاً',
    sortTitleAZ: 'العنوان أ–ي',
    sortTitleZA: 'العنوان ي–أ',

    // ── Batch operations ──────────────────────────────────────────────────────
    selectAll: 'تحديد الكل',
    deselectAll: 'إلغاء التحديد',
    selectedCount: (n) => `${n} محدد`,
    batchDelete: 'نقل إلى المهملات',
    batchAddTag: '+ وسم',
    batchTagApply: 'تطبيق',
    batchDeleteConfirm: (n) => `نقل ${n} فيديو إلى المهملات؟`,

    // ── Trash ─────────────────────────────────────────────────────────────────
    trash: 'المهملات',
    trashEmpty: 'المهملات فارغة',
    trashNotice: 'تُحذف العناصر نهائياً بعد 30 يوماً',
    trashDaysLeft: (n) => `${n} يوم متبقٍ`,
    restore: 'استعادة',
    deleteForever: 'حذف نهائي',
    deleteForeverConfirm: 'هل تريد الحذف النهائي؟ لا يمكن التراجع.',
    emptyTrash: 'إفراغ المهملات',
    emptyTrashConfirm: 'حذف جميع العناصر في المهملات نهائياً؟',
  },
}
