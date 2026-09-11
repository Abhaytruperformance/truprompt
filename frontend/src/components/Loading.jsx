import React, { useEffect, useState } from 'react'
import './CSS/Loading.css'

// variant="generate" -- the signature "AI is writing your prompt" moment
// (PromptResults.jsx's loading branch only). Delays showing anything for
// ~300ms so a fast response never flashes a loader that immediately
// disappears -- the timer is cleared on unmount so a fast completion can't
// trigger a state update after this component is gone.
//
// variant="inline" (default) -- the small quiet indicator reused everywhere
// else (app boot, panel loads) instead of each screen inlining its own gif.
const Loading = ({ variant = 'inline', label }) => {
    const [showGenerate, setShowGenerate] = useState(false)

    useEffect(() => {
        if (variant !== 'generate') return undefined
        const timer = setTimeout(() => setShowGenerate(true), 300)
        return () => clearTimeout(timer)
    }, [variant])

    if (variant === 'generate') {
        if (!showGenerate) return null
        return (
            <div className="loadingGenerate" role="status" aria-live="polite">
                <div className="loadingGenerateLines" aria-hidden="true">
                    <span className="loadingGenerateLine" style={{ width: '40%' }} />
                    <span className="loadingGenerateLine" style={{ width: '70%' }} />
                    <span className="loadingGenerateLine" style={{ width: '55%' }} />
                </div>
                <p className="loadingGenerateLabel">{label || 'Generating your prompt…'}</p>
            </div>
        )
    }

    return (
        <div className="loadingInline" role="status" aria-live="polite">
            <span className="loadingInlineDot" aria-hidden="true" />
            {label && <span className="loadingInlineLabel">{label}</span>}
        </div>
    )
}

export default Loading
