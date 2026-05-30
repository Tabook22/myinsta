import { useEffect, useState } from 'react'
import { getStats } from '../api/client.js'
import { useLanguage } from '../context/LanguageContext.jsx'

function StatItem({ icon, value, label }) {
  return (
    <div className="stat-item">
      <span className="stat-icon">{icon}</span>
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  )
}

function formatDuration(totalSeconds) {
  const hours = totalSeconds / 3600
  if (hours < 1) return `${Math.round(totalSeconds / 60)}m`
  return `${hours.toFixed(1)}h`
}

export default function StatsPanel() {
  const { t } = useLanguage()
  const [stats, setStats] = useState(null)

  useEffect(() => {
    getStats().then(setStats).catch(() => {/* silently fail */})
  }, [])

  // Don't render until stats loaded or if all zeros
  if (!stats || stats.total_videos === 0) return null

  return (
    <div className="stats-panel">
      <StatItem
        icon="📚"
        value={stats.total_videos}
        label={t('statsVideos')}
      />
      <StatItem
        icon="✅"
        value={stats.ready_videos}
        label={t('statsTranscribed')}
      />
      <StatItem
        icon="⏱"
        value={formatDuration(stats.total_duration_seconds)}
        label={t('statsHours')}
      />
      <StatItem
        icon="💬"
        value={stats.total_chats}
        label={t('statsChats')}
      />
    </div>
  )
}
