import React, { useState } from 'react'
import { useAcceptInviteMutation } from '../store/slices/orgSlice'

const AcceptInvitePage = ({ userData, isLoading }) => {
    const token = new URLSearchParams(window.location.search).get('token');
    const [acceptInvite, { isLoading: accepting }] = useAcceptInviteMutation();
    const [result, setResult] = useState(null); // 'success' | 'error' | null

    if (isLoading) {
        return (
            <div className="container d-flex justify-content-center mt-5" style={{ background: 'var(--bg-page)', minHeight: '100vh' }}>
                <div className="card cardEmptyState" style={{ maxWidth: 420, width: '100%' }}>Loading...</div>
            </div>
        );
    }

    if (!userData) {
        return (
            <div className="container d-flex justify-content-center mt-5" style={{ background: 'var(--bg-page)', minHeight: '100vh' }}>
                <div className="card" style={{ maxWidth: 420, width: '100%' }}>
                    <h3 className="cardTitle">You need to log in first</h3>
                    <p style={{ color: 'var(--text-secondary)' }}>Log in, then revisit this same invitation link to accept it.</p>
                    <a className="btn-primary" style={{ display: 'inline-block', textDecoration: 'none' }} href={`${process.env.REACT_APP_BACKEND_URL}/api/users/auth/microsoft`}>Log in</a>
                </div>
            </div>
        );
    }

    const handleAccept = async () => {
        try {
            await acceptInvite(token).unwrap();
            setResult('success');
        } catch (err) {
            setResult('error');
        }
    };

    return (
        <div className="container d-flex justify-content-center mt-5" style={{ background: 'var(--bg-page)', minHeight: '100vh' }}>
            <div className="card" style={{ maxWidth: 420, width: '100%' }}>
                <h3 className="cardTitle">Accept invitation</h3>
                {result === 'success' ? (
                    <>
                        <p style={{ color: 'var(--status-success)' }}>You've joined the organization.</p>
                        <a className="btn-primary" style={{ display: 'inline-block', textDecoration: 'none' }} href="/">Go to the app</a>
                    </>
                ) : result === 'error' ? (
                    <p style={{ color: 'var(--status-danger)' }}>This invitation could not be accepted (it may be expired or already used).</p>
                ) : (
                    <button className="btn-primary" onClick={handleAccept} disabled={accepting}>
                        {accepting ? 'Accepting...' : 'Accept invitation'}
                    </button>
                )}
            </div>
        </div>
    );
}

export default AcceptInvitePage
