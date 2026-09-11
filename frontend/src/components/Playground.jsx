import React, { useState } from 'react'
import Swal from 'sweetalert2'
import '@sweetalert2/theme-dark'
import { useGetModelsQuery } from '../store/slices/orgSlice'
import { useUpdatePromptCountMutation } from '../store/slices/truPromptSlice'
import { generateWithModel } from './openAIUtils'
import SaveModal from './SaveModal'
import copy from '../assets/copy.svg'
import save from '../assets/save.svg'
import regenerate from '../assets/regenerate.svg'
import './CSS/Playground.css'

const MAX_COMPARE_MODELS = 5;

const Playground = () => {
    const { data: models = [] } = useGetModelsQuery();
    const [mostUsedPromptCount] = useUpdatePromptCountMutation();

    const [prompt, setPrompt] = useState('');
    const [selectedModelIds, setSelectedModelIds] = useState([]);
    // Keyed by modelId -- independent per-card state so one slow/failed model
    // never blocks the others from rendering as soon as they resolve.
    const [cardStatus, setCardStatus] = useState({}); // { [modelId]: 'loading' | 'done' | 'error' }
    const [cardError, setCardError] = useState({});   // { [modelId]: message }
    const [results, setResults] = useState([]);       // flat array of generate results, same shape SaveModal expects

    const [showSaveDialog, setShowSaveDialog] = useState(false);
    const [selectedPrompt, setSelectedPrompt] = useState(null);
    const handleShow = (result) => {
        setSelectedPrompt(result);
        setShowSaveDialog(true);
    };

    const isComparing = Object.values(cardStatus).some((s) => s === 'loading');

    const toggleModel = (modelId) => {
        setSelectedModelIds((prev) =>
            prev.includes(modelId)
                ? prev.filter((id) => id !== modelId)
                : prev.length < MAX_COMPARE_MODELS ? [...prev, modelId] : prev
        );
    };

    const runModel = async (modelId) => {
        setCardStatus((prev) => ({ ...prev, [modelId]: 'loading' }));
        setCardError((prev) => ({ ...prev, [modelId]: null }));
        try {
            const data = await generateWithModel(prompt, [], modelId, null, false);
            setResults((prev) => [...prev.filter((r) => r._modelId !== modelId), { ...data, _modelId: modelId }]);
            setCardStatus((prev) => ({ ...prev, [modelId]: 'done' }));
        } catch (err) {
            const message = err.code === 429
                ? 'Rate-limited by the AI provider. Try again shortly.'
                : 'Something went wrong generating with this model.';
            setCardError((prev) => ({ ...prev, [modelId]: message }));
            setCardStatus((prev) => ({ ...prev, [modelId]: 'error' }));
        }
    };

    const handleCompare = (e) => {
        e.preventDefault();
        if (!prompt.trim() || selectedModelIds.length === 0 || isComparing) return;
        // Each model runs and updates its own card independently -- not
        // awaited together -- so a fast model's result shows up immediately
        // instead of waiting for the slowest one in the batch.
        selectedModelIds.forEach((modelId) => runModel(modelId));
    };

    const copyToClipboard = async (result) => {
        if (!navigator.clipboard) return;
        try {
            await navigator.clipboard.writeText(result.prompt);
            Swal.fire({ toast: true, position: 'top-end', showConfirmButton: false, timer: 2000, icon: 'success', title: 'Copied' });
            if (result._id || result.promptDBId) {
                await mostUsedPromptCount(result._id || result.promptDBId).unwrap();
            }
        } catch {
            Swal.fire({ icon: 'error', title: 'Could not copy', text: 'Please copy manually' });
        }
    };

    return (
        <div className="playgroundPanel w-100">
            <h3 className="cardTitle" style={{ marginBottom: 'var(--space-6)' }}>Playground</h3>

            <div className="card">
                <form onSubmit={handleCompare}>
                    <div className="formGroup">
                        <label htmlFor="playgroundPrompt">Prompt</label>
                        <textarea
                            id="playgroundPrompt"
                            className="playgroundTextarea"
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            placeholder="Describe what you want a prompt for..."
                            rows={3}
                        />
                    </div>
                    <div className="formGroup">
                        <label>Compare models (up to {MAX_COMPARE_MODELS})</label>
                        <div className="playgroundModelList">
                            {models.map((m) => (
                                <label key={m.id} className="playgroundModelCheck">
                                    <input
                                        type="checkbox"
                                        checked={selectedModelIds.includes(m.id)}
                                        onChange={() => toggleModel(m.id)}
                                        disabled={!selectedModelIds.includes(m.id) && selectedModelIds.length >= MAX_COMPARE_MODELS}
                                    />
                                    {m.label}
                                </label>
                            ))}
                        </div>
                    </div>
                    <button
                        className="btn-primary"
                        type="submit"
                        disabled={!prompt.trim() || selectedModelIds.length === 0 || isComparing}
                    >
                        {isComparing ? 'Comparing...' : 'Compare'}
                    </button>
                </form>
            </div>

            {selectedModelIds.length > 0 && (
                <div className="playgroundGrid">
                    {selectedModelIds.map((modelId) => {
                        const status = cardStatus[modelId];
                        const result = results.find((r) => r._modelId === modelId);
                        const label = models.find((m) => m.id === modelId)?.label || modelId;
                        return (
                            <div key={modelId} className="card">
                                <div className="d-flex justify-content-between align-items-center flex-wrap" style={{ marginBottom: 'var(--space-3)', gap: 'var(--space-2)' }}>
                                    <span className="pill pill--info">{label}</span>
                                    <div className="d-flex gap-2 flex-wrap">
                                        {result && (
                                            <span className="pill" title="Response time">⏱ {(result.modelLatencyMs / 1000).toFixed(1)}s</span>
                                        )}
                                        {result?.totalTokens != null && (
                                            <span className="pill" title={`${result.promptTokens} prompt + ${result.completionTokens} completion`}>
                                                {result.totalTokens} tokens
                                            </span>
                                        )}
                                        {result?.fallbackUsed && (
                                            <span className="pill pill--warning" title={`Fell back to ${result.modelUsed}`}>fallback used</span>
                                        )}
                                    </div>
                                </div>
                                {status === 'loading' && <div className="cardEmptyState">Generating...</div>}
                                {status === 'error' && <div className="cardEmptyState">{cardError[modelId]}</div>}
                                {status === 'done' && result && (
                                    <>
                                        <h6 className="promptResultTitle">Optimizer</h6>
                                        <pre className="promptResultContent">{result.optimizer}</pre>
                                        <h6 className="promptResultTitle">Prompt</h6>
                                        <pre className="promptResultContent">{result.prompt}</pre>
                                        <div className="d-flex actionButtonDiv mt-3">
                                            <img src={copy} alt="Copy" width={15} height={15} title="Copy" onClick={() => copyToClipboard(result)} role="button" />
                                            <img src={save} alt="Save" width={15} height={15} title="Save" onClick={() => handleShow(result)} role="button" />
                                            <img src={regenerate} alt="Regenerate" width={15} height={15} title="Regenerate this model" onClick={() => runModel(modelId)} role="button" />
                                        </div>
                                    </>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            <SaveModal
                selectedPrompt={selectedPrompt}
                handleShow={handleShow}
                show={showSaveDialog}
                setShowSaveDialog={setShowSaveDialog}
                setOpenAIResults={setResults}
                id={selectedPrompt ? selectedPrompt.id : null}
            />
        </div>
    )
}

export default Playground
