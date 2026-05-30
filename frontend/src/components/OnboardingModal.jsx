import { useState } from 'react'
import { useLanguage } from '../context/LanguageContext.jsx'

const STORAGE_KEY = 'myinsta-onboarding-done'

const STEPS = [
  {
    icon: '🔗',
    titleKey: 'onboardingStep1Title',
    descKey: 'onboardingStep1Desc',
  },
  {
    icon: '🤖',
    titleKey: 'onboardingStep2Title',
    descKey: 'onboardingStep2Desc',
  },
  {
    icon: '💬',
    titleKey: 'onboardingStep3Title',
    descKey: 'onboardingStep3Desc',
  },
]

export function shouldShowOnboarding() {
  return !localStorage.getItem(STORAGE_KEY)
}

export function markOnboardingDone() {
  localStorage.setItem(STORAGE_KEY, '1')
}

export default function OnboardingModal({ onDone }) {
  const { t } = useLanguage()
  const [activeStep, setActiveStep] = useState(0)

  function handleDone() {
    markOnboardingDone()
    onDone()
  }

  return (
    <div className="onboarding-backdrop" onClick={handleDone}>
      <div
        className="onboarding-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="onboarding-title"
      >
        {/* Header */}
        <div className="onboarding-header">
          <h2 id="onboarding-title">{t('onboardingTitle')}</h2>
          <p>{t('onboardingSubtitle')}</p>
        </div>

        {/* Steps */}
        <div className="onboarding-steps">
          {STEPS.map((step, idx) => (
            <div
              key={idx}
              className={`onboarding-step${activeStep === idx ? ' onboarding-step-active' : ''}`}
              onClick={() => setActiveStep(idx)}
            >
              <span className="onboarding-step-icon">{step.icon}</span>
              <div className="onboarding-step-body">
                <strong>{t(step.titleKey)}</strong>
                <span>{t(step.descKey)}</span>
              </div>
              <span className="onboarding-step-num">{idx + 1}</span>
            </div>
          ))}
        </div>

        {/* Step dots */}
        <div className="onboarding-dots">
          {STEPS.map((_, idx) => (
            <button
              key={idx}
              type="button"
              className={`onboarding-dot${activeStep === idx ? ' onboarding-dot-active' : ''}`}
              onClick={() => setActiveStep(idx)}
              aria-label={`Step ${idx + 1}`}
            />
          ))}
        </div>

        {/* CTA */}
        <button type="button" className="onboarding-cta" onClick={handleDone}>
          {t('onboardingGetStarted')}
        </button>
      </div>
    </div>
  )
}
