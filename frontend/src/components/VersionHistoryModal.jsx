import React, { useMemo, useState } from 'react'
import { Modal, Button } from 'react-bootstrap'
import { diffWords } from 'diff'
import Swal from 'sweetalert2'
import { useRestorePromptVersionMutation } from '../store/slices/truPromptSlice'
import './CSS/VersionHistory.css'

const FIELDS = [
    { key: 'category', label: 'Category' },
    { key: 'userPrompt', label: 'Your Request' },
    { key: 'prompt', label: 'Prompt' },
    { key: 'optimizer', label: 'Optimizer' },
];

const CURRENT = 'current';

const showError = (title, err) => {
    Swal.fire({ icon: 'error', title, text: err?.data?.detail || 'Something went wrong' });
};

const DiffBlock = ({ label, before, after }) => {
    if ((before || '') === (after || '')) return null;
    const parts = diffWords(before || '', after || '');
    return (
        <div className="formGroup">
            <label>{label}</label>
            <div className="diffPanel">
                {parts.map((part, i) => (
                    <span
                        key={i}
                        className={part.added ? 'diffAdded' : part.removed ? 'diffRemoved' : undefined}
                    >
                        {part.value}
                    </span>
                ))}
            </div>
        </div>
    );
};

const VersionHistoryModal = ({ show, onClose, promptId, currentPrompt, versions }) => {
    const [restorePromptVersion] = useRestorePromptVersionMutation();

    const sorted = useMemo(() => [...versions].sort((a, b) => b.versionNumber - a.versionNumber), [versions]);
    const [fromVersionId, setFromVersionId] = useState(sorted[0]?._id || CURRENT);
    const [toVersionId, setToVersionId] = useState(CURRENT);

    const contentFor = (id) => {
        if (id === CURRENT) return currentPrompt;
        return sorted.find((v) => v._id === id) || {};
    };
    const fromContent = contentFor(fromVersionId);
    const toContent = contentFor(toVersionId);

    const handleRestore = async () => {
        if (fromVersionId === CURRENT) return;
        try {
            await restorePromptVersion({ id: promptId, versionId: fromVersionId }).unwrap();
            Swal.fire({ icon: 'success', title: 'Version restored' });
            onClose();
        } catch (err) {
            showError('Could not restore version', err);
        }
    };

    const versionLabel = (v) => {
        const when = new Date(v.createdAt).toLocaleString();
        return `v${v.versionNumber} — ${when}`;
    };

    return (
        <Modal show={show} onHide={onClose} className="customModal" size="lg">
            <Modal.Header closeButton>
                <Modal.Title>Version history</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <div className="d-flex gap-3 formGroup">
                    <div style={{ flex: 1 }}>
                        <label>From</label>
                        <select className="w-100" value={fromVersionId} onChange={(e) => setFromVersionId(e.target.value)}>
                            {sorted.map((v) => <option key={v._id} value={v._id}>{versionLabel(v)}</option>)}
                            <option value={CURRENT}>Current</option>
                        </select>
                    </div>
                    <div style={{ flex: 1 }}>
                        <label>To</label>
                        <select className="w-100" value={toVersionId} onChange={(e) => setToVersionId(e.target.value)}>
                            <option value={CURRENT}>Current</option>
                            {sorted.map((v) => <option key={v._id} value={v._id}>{versionLabel(v)}</option>)}
                        </select>
                    </div>
                </div>

                {FIELDS.map((f) => (
                    <DiffBlock key={f.key} label={f.label} before={fromContent[f.key]} after={toContent[f.key]} />
                ))}
                {FIELDS.every((f) => (fromContent[f.key] || '') === (toContent[f.key] || '')) && (
                    <div className="cardEmptyState">No differences between these two.</div>
                )}
            </Modal.Body>
            <Modal.Footer>
                <Button className="SaveBtn" variant="primary" onClick={handleRestore} disabled={fromVersionId === CURRENT}>
                    Restore "From" version
                </Button>
            </Modal.Footer>
        </Modal>
    );
}

export default VersionHistoryModal
