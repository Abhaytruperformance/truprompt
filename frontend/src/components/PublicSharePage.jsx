import React, { useEffect, useState } from 'react'

const getToken = () => window.location.pathname.split('/share/')[1];

const PageWrap = ({ children }) => (
    <div className="container d-flex justify-content-center mt-5" style={{ background: 'var(--bg-page)', minHeight: '100vh' }}>
        <div className="card" style={{ maxWidth: 640, width: '100%' }}>{children}</div>
    </div>
);

const PublicSharePage = () => {
    const token = getToken();
    const [prompt, setPrompt] = useState(null);
    const [needsPassword, setNeedsPassword] = useState(false);
    const [passwordInput, setPasswordInput] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(true);
    const [regenerating, setRegenerating] = useState(false);
    const [regenerateMessage, setRegenerateMessage] = useState('');

    const fetchShare = async (password) => {
        setLoading(true);
        setError('');
        try {
            // Password goes in the POST body, never a URL query param -- query
            // strings get logged server-side, kept in browser history, and
            // can leak via the Referer header.
            const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/public/shares/${token}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: password || null }),
            });
            if (res.status === 403) {
                const body = await res.json();
                setNeedsPassword(true);
                if (body.detail === 'Incorrect password') setError('Incorrect password, try again.');
                return;
            }
            if (res.status === 404) {
                setError('This share link is invalid, expired, or has been revoked.');
                return;
            }
            const body = await res.json();
            setPrompt(body.prompt);
            setNeedsPassword(false);
        } catch (err) {
            setError('Could not load this shared prompt.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchShare();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handlePasswordSubmit = (e) => {
        e.preventDefault();
        fetchShare(passwordInput);
    };

    const handleRegenerate = async () => {
        setRegenerating(true);
        setRegenerateMessage('');
        try {
            const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/public/shares/${token}/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: passwordInput || null }),
            });
            const body = await res.json();
            if (res.status === 403 && body.detail?.includes('generation limit')) {
                setRegenerateMessage("This share link has reached its generation limit -- no more regenerations are available.");
                return;
            }
            if (!res.ok) {
                setRegenerateMessage(body.detail || 'Could not regenerate this prompt.');
                return;
            }
            setPrompt((prev) => ({ ...prev, optimizer: body.optimizer, prompt: body.prompt }));
        } catch (err) {
            setRegenerateMessage('Could not regenerate this prompt.');
        } finally {
            setRegenerating(false);
        }
    };

    if (loading) {
        return <PageWrap><div className="cardEmptyState">Loading...</div></PageWrap>;
    }

    if (needsPassword) {
        return (
            <PageWrap>
                <h3 className="cardTitle">This prompt is password protected</h3>
                <form onSubmit={handlePasswordSubmit} className="d-flex gap-2 formGroup">
                    <input
                        type="password"
                        placeholder="Enter password"
                        value={passwordInput}
                        onChange={(e) => setPasswordInput(e.target.value)}
                    />
                    <button className="btn-primary" type="submit">View</button>
                </form>
                {error && <p style={{ color: 'var(--status-danger)' }}>{error}</p>}
            </PageWrap>
        );
    }

    if (error) {
        return <PageWrap><p style={{ color: 'var(--status-danger)' }}>{error}</p></PageWrap>;
    }

    return (
        <PageWrap>
            <h3 className="cardTitle">{prompt.category}</h3>
            <p style={{ color: 'var(--text-secondary)' }}>{prompt.userPrompt}</p>
            <h6 style={{ color: 'var(--text-primary)', marginTop: 'var(--space-4)' }}>Optimizer</h6>
            <pre style={{ color: 'var(--text-secondary)', whiteSpace: 'pre-wrap' }}>{prompt.optimizer}</pre>
            <h6 style={{ color: 'var(--text-primary)', marginTop: 'var(--space-4)' }}>Prompt</h6>
            <pre style={{ color: 'var(--text-secondary)', whiteSpace: 'pre-wrap' }}>{prompt.prompt}</pre>
            <button
                type="button"
                className="btn-secondary mt-3"
                onClick={handleRegenerate}
                disabled={regenerating}
            >
                {regenerating ? 'Regenerating...' : 'Regenerate'}
            </button>
            {regenerateMessage && (
                <p style={{ color: 'var(--status-danger)', marginTop: 'var(--space-2)' }}>{regenerateMessage}</p>
            )}
        </PageWrap>
    );
}

export default PublicSharePage
