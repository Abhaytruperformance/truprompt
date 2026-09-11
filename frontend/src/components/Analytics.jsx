import React from 'react'
import { useGetAnalyticsQuery } from '../store/slices/orgSlice'
import Loading from './Loading'
import './CSS/Analytics.css'

const SOURCE_LABEL = { web: 'Web', api: 'Public API', mcp: 'MCP' };

const Analytics = () => {
    const { data, isLoading } = useGetAnalyticsQuery();

    if (isLoading || !data) {
        return <div className="analyticsPanel w-100 d-flex justify-content-center"><Loading /></div>;
    }

    const generationsThisWeek = data.generationsByDay.slice(-7).reduce((sum, d) => sum + d.count, 0);
    const maxDayCount = Math.max(1, ...data.generationsByDay.map((d) => d.count));

    return (
        <div className="analyticsPanel w-100">
            <h3 className="cardTitle" style={{ marginBottom: 'var(--space-6)' }}>Analytics</h3>

            <div className="statCardsRow">
                <div className="statCard">
                    <div className="statCardNumber">{data.totalGenerations}</div>
                    <div className="statCardLabel">Generations (30d)</div>
                </div>
                <div className="statCard">
                    <div className="statCardNumber">{generationsThisWeek}</div>
                    <div className="statCardLabel">Generations (7d)</div>
                </div>
                <div className="statCard">
                    <div className="statCardNumber">{data.mostUsedModel || '—'}</div>
                    <div className="statCardLabel">Most-used model</div>
                </div>
                <div className="statCard">
                    <div className="statCardNumber">{data.activeApiKeys}</div>
                    <div className="statCardLabel">Active API keys (7d)</div>
                </div>
            </div>

            <div className="card">
                <h5 className="cardTitle">Generations per day (last 30 days)</h5>
                {data.generationsByDay.length === 0 ? (
                    <div className="cardEmptyState">No generations yet</div>
                ) : (
                    <div className="analyticsSparkline">
                        {data.generationsByDay.map((d) => (
                            <div
                                key={d.date}
                                className="analyticsBar"
                                title={`${d.date}: ${d.count}`}
                                style={{ height: `${(d.count / maxDayCount) * 100}%` }}
                            />
                        ))}
                    </div>
                )}
                <div className="d-flex gap-3" style={{ marginTop: 'var(--space-4)' }}>
                    {Object.entries(SOURCE_LABEL).map(([key, label]) => (
                        <span key={key} className="pill pill--info">{label}: {data.generationsBySource[key] || 0}</span>
                    ))}
                </div>
            </div>

            <div className="card">
                <h5 className="cardTitle">Most Copied Prompts</h5>
                <p className="helperText" style={{ marginTop: '-8px', marginBottom: 'var(--space-4)' }}>
                    Based on how often a prompt's text has been copied, not how often it's been generated.
                </p>
                {data.mostCopiedPrompts.length === 0 ? (
                    <div className="cardEmptyState">No prompts copied yet</div>
                ) : (
                    <ul className="manageList">
                        {data.mostCopiedPrompts.map((p) => (
                            <li key={p.id} className="d-flex justify-content-between align-items-center">
                                <span className="analyticsPromptCell" title={p.userPrompt}>{p.userPrompt}</span>
                                <span className="pill pill--success">{p.count} copies</span>
                            </li>
                        ))}
                    </ul>
                )}
            </div>

            <div className="card">
                <h5 className="cardTitle">Top Rated Prompts</h5>
                {data.topRatedPrompts.length === 0 ? (
                    <div className="cardEmptyState">No ratings yet</div>
                ) : (
                    <ul className="manageList">
                        {data.topRatedPrompts.map((p) => (
                            <li key={p.id} className="d-flex justify-content-between align-items-center">
                                <span className="analyticsPromptCell" title={p.userPrompt}>{p.userPrompt}</span>
                                <span className="pill pill--warning">★ {p.avgRating} ({p.ratingCount})</span>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    )
}

export default Analytics
