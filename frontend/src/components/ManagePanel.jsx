import React, { useState } from 'react'
import Swal from 'sweetalert2'
import {
    useGetDepartmentsQuery,
    useCreateDepartmentMutation,
    useDeleteDepartmentMutation,
    useGetCustomFieldsQuery,
    useCreateCustomFieldMutation,
    useDeleteCustomFieldMutation,
    useGetTagsQuery,
    useCreateTagMutation,
    useDeleteTagMutation,
    useGetApiKeysQuery,
    useCreateApiKeyMutation,
    useRevokeApiKeyMutation,
    useGetMyOrgQuery,
} from '../store/slices/orgSlice'
import {
    useGetPromptsQuery,
    useUpdatePromptMutation,
    useUpdatePromptCustomFieldsMutation,
    useUpdatePromptTagsMutation,
    useUpdatePromptStatusMutation,
    useDeletePromptMutation,
    useLazyGetPromptVersionsQuery,
    useCreateShareMutation,
} from '../store/slices/truPromptSlice'
import Loading from './Loading'
import VersionHistoryModal from './VersionHistoryModal'
import './CSS/ManagePanel.css'

const FIELD_TYPES = ['text', 'number', 'select', 'date'];
const FIELD_TYPE_PILL = { text: 'pill--info', number: 'pill--success', select: 'pill--warning', date: 'pill--danger' };
const STATUSES = ['draft', 'review', 'approved', 'archived'];
const STATUS_LABEL = { draft: 'Draft', review: 'Review', approved: '✓ Approved', archived: 'Archived' };

const confirmAction = async (title, text) => {
    const result = await Swal.fire({
        icon: 'warning',
        title,
        text,
        showCancelButton: true,
        confirmButtonText: 'Yes',
    });
    return result.isConfirmed;
};

const showError = (title, err) => {
    Swal.fire({
        icon: 'error',
        title,
        text: err?.data?.detail || 'Something went wrong',
    });
};

const showToast = (title) => {
    Swal.fire({ toast: true, position: 'top-end', showConfirmButton: false, timer: 2000, icon: 'success', title });
};

const ManagePanel = () => {
    const { data: departments = [], isLoading: deptLoading } = useGetDepartmentsQuery();
    const { data: customFields = [], isLoading: fieldsLoading } = useGetCustomFieldsQuery();
    const { data: tags = [], isLoading: tagsLoading } = useGetTagsQuery();
    const { data: apiKeys = [], isLoading: keysLoading } = useGetApiKeysQuery();
    // status: 'all' -- this is the admin management view, it should show every
    // prompt regardless of review state, not just the curated/approved ones.
    const { data: prompts = [], isLoading: promptsLoading } = useGetPromptsQuery({ status: 'all' });
    const { data: orgData } = useGetMyOrgQuery();
    const isAdmin = orgData?.role === 'admin' || orgData?.role === 'owner';

    const [createDepartment] = useCreateDepartmentMutation();
    const [deleteDepartment] = useDeleteDepartmentMutation();
    const [createCustomField] = useCreateCustomFieldMutation();
    const [deleteCustomField] = useDeleteCustomFieldMutation();
    const [createTag] = useCreateTagMutation();
    const [deleteTag] = useDeleteTagMutation();
    const [createApiKey] = useCreateApiKeyMutation();
    const [revokeApiKey] = useRevokeApiKeyMutation();
    const [updatePrompt] = useUpdatePromptMutation();
    const [updatePromptCustomFields] = useUpdatePromptCustomFieldsMutation();
    const [updatePromptTags] = useUpdatePromptTagsMutation();
    const [updatePromptStatus] = useUpdatePromptStatusMutation();
    const [deletePrompt] = useDeletePromptMutation();
    const [triggerGetVersions] = useLazyGetPromptVersionsQuery();
    const [createShare] = useCreateShareMutation();

    const [deptName, setDeptName] = useState('');
    const [fieldName, setFieldName] = useState('');
    const [fieldType, setFieldType] = useState('text');
    const [fieldOptions, setFieldOptions] = useState('');
    const [tagName, setTagName] = useState('');
    const [apiKeyName, setApiKeyName] = useState('');
    const [apiKeyScopeRead, setApiKeyScopeRead] = useState(true);
    const [apiKeyScopeGenerate, setApiKeyScopeGenerate] = useState(true);
    const [historyPromptId, setHistoryPromptId] = useState(null);
    const [historyVersions, setHistoryVersions] = useState([]);
    const [showVersionHistory, setShowVersionHistory] = useState(false);

    const handleAddDepartment = async (e) => {
        e.preventDefault();
        try {
            await createDepartment(deptName).unwrap();
            setDeptName('');
            showToast('Department added');
        } catch (err) {
            showError('Could not add department', err);
        }
    };

    const handleDeleteDepartment = async (id, name) => {
        if (!(await confirmAction('Delete this department?', name))) return;
        try {
            await deleteDepartment(id).unwrap();
            showToast('Department deleted');
        } catch (err) {
            showError('Could not delete department', err);
        }
    };

    const handleAddField = async (e) => {
        e.preventDefault();
        const options = fieldType === 'select'
            ? fieldOptions.split(',').map((o) => o.trim()).filter(Boolean)
            : undefined;
        try {
            await createCustomField({ name: fieldName, fieldType, options }).unwrap();
            setFieldName('');
            setFieldOptions('');
            showToast('Custom field added');
        } catch (err) {
            showError('Could not add custom field', err);
        }
    };

    const handleDeleteField = async (id, name) => {
        if (!(await confirmAction('Delete this custom field?', name))) return;
        try {
            await deleteCustomField(id).unwrap();
            showToast('Custom field deleted');
        } catch (err) {
            showError('Could not delete custom field', err);
        }
    };

    const handleDepartmentAssign = async (promptId, departmentId) => {
        try {
            await updatePrompt({ id: promptId, departmentId: departmentId || null }).unwrap();
            showToast('Department updated');
        } catch (err) {
            showError('Could not update department', err);
        }
    };

    const handleStatusChange = async (promptId, newStatus) => {
        try {
            await updatePromptStatus({ id: promptId, status: newStatus }).unwrap();
            showToast('Status updated');
        } catch (err) {
            showError('Could not update status', err);
        }
    };

    const handleFieldValueChange = async (promptId, fieldDefId, value) => {
        try {
            await updatePromptCustomFields({ id: promptId, values: { [fieldDefId]: value } }).unwrap();
            showToast('Field updated');
        } catch (err) {
            showError('Could not update field value', err);
        }
    };

    const handleDeletePrompt = async (id, userPrompt) => {
        if (!(await confirmAction('Delete this prompt?', userPrompt))) return;
        try {
            await deletePrompt(id).unwrap();
            showToast('Prompt deleted');
        } catch (err) {
            showError('Could not delete prompt', err);
        }
    };

    const handleAddTag = async (e) => {
        e.preventDefault();
        try {
            await createTag(tagName).unwrap();
            setTagName('');
            showToast('Tag added');
        } catch (err) {
            showError('Could not add tag', err);
        }
    };

    const handleDeleteTag = async (id, name) => {
        if (!(await confirmAction('Delete this tag?', name))) return;
        try {
            await deleteTag(id).unwrap();
            showToast('Tag deleted');
        } catch (err) {
            showError('Could not delete tag', err);
        }
    };

    const handleTagsChange = async (promptId, tagIds) => {
        try {
            await updatePromptTags({ id: promptId, tagIds }).unwrap();
            showToast('Tags updated');
        } catch (err) {
            showError('Could not update tags', err);
        }
    };

    const handleShowHistory = async (promptId) => {
        try {
            const versions = await triggerGetVersions(promptId).unwrap();
            if (versions.length === 0) {
                Swal.fire({ icon: 'info', title: 'No history yet', text: 'This prompt has not been edited yet.' });
                return;
            }
            setHistoryPromptId(promptId);
            setHistoryVersions(versions);
            setShowVersionHistory(true);
        } catch (err) {
            showError('Could not load history', err);
        }
    };

    const handleShare = async (promptId) => {
        const { value: formValues, isConfirmed } = await Swal.fire({
            title: 'Create a share link',
            html: `
                <input id="swal-share-password" class="swal2-input" type="text" placeholder="Optional password">
                <input id="swal-share-limit" class="swal2-input" type="number" min="1" placeholder="Generation limit (default 20)">
                <label style="display:flex;align-items:center;gap:6px;margin-top:8px;font-size:13px">
                    <input id="swal-share-unlimited" type="checkbox"> Unlimited generations (not recommended -- anonymous visitors can run up AI usage)
                </label>
            `,
            focusConfirm: false,
            showCancelButton: true,
            confirmButtonText: 'Create link',
            preConfirm: () => ({
                password: document.getElementById('swal-share-password').value,
                generationLimit: document.getElementById('swal-share-limit').value,
                unlimited: document.getElementById('swal-share-unlimited').checked,
            }),
        });
        if (!isConfirmed) return;
        try {
            const share = await createShare({
                id: promptId,
                password: formValues.password,
                // Explicit null (not omitted) is what actually requests
                // unlimited -- omitting the field gets the server's safe
                // default instead. A blank, non-unlimited field falls back
                // to that same default rather than sending an invalid value.
                generationLimit: formValues.unlimited
                    ? null
                    : (formValues.generationLimit ? Number(formValues.generationLimit) : undefined),
            }).unwrap();
            const link = `${window.location.origin}/share/${share.token}`;
            if (navigator.clipboard) await navigator.clipboard.writeText(link);
            Swal.fire({ icon: 'success', title: 'Link copied to clipboard', text: link });
        } catch (err) {
            showError('Could not create share link', err);
        }
    };

    const handleAddApiKey = async (e) => {
        e.preventDefault();
        const scopes = [
            ...(apiKeyScopeRead ? ['library:read'] : []),
            ...(apiKeyScopeGenerate ? ['prompts:generate'] : []),
        ];
        try {
            const result = await createApiKey({ name: apiKeyName, scopes }).unwrap();
            setApiKeyName('');
            await Swal.fire({
                icon: 'success',
                title: 'API key created',
                html: `<p>Copy this now — it won't be shown again:</p><code style="word-break:break-all">${result.key}</code>`,
                confirmButtonText: "I've copied it",
            });
        } catch (err) {
            showError('Could not create API key', err);
        }
    };

    const handleRevokeApiKey = async (id, name) => {
        if (!(await confirmAction('Revoke this API key?', name))) return;
        try {
            await revokeApiKey(id).unwrap();
            showToast('API key revoked');
        } catch (err) {
            showError('Could not revoke API key', err);
        }
    };

    const mcpUrl = `${process.env.REACT_APP_BACKEND_URL}/mcp/`;
    const apiOrigin = process.env.REACT_APP_BACKEND_URL;
    const curlSnippet = `curl -X POST "${apiOrigin}/v1/prompts/PROMPT_ID/generate" \\\n  -H "Authorization: Bearer YOUR_API_KEY"`;
    const jsSnippet = `fetch("${apiOrigin}/v1/prompts/PROMPT_ID/generate", {\n  method: "POST",\n  headers: { Authorization: "Bearer YOUR_API_KEY" },\n})\n  .then((r) => r.json())\n  .then(console.log);`;

    const handleCopyMcpUrl = async () => {
        if (navigator.clipboard) await navigator.clipboard.writeText(mcpUrl);
        showToast('MCP URL copied');
    };

    const handleCopySnippet = async (text) => {
        if (navigator.clipboard) await navigator.clipboard.writeText(text);
        showToast('Copied');
    };

    const handleShowSource = (p) => {
        // p.sourceName/sourceContext are user-controlled (an uploaded filename or a
        // pasted URL, and the extracted page/file text) -- titleText and textContent
        // keep them as plain text so a crafted filename/URL/content can't execute as
        // HTML/script in another org member's browser when they view this prompt.
        const pre = document.createElement('pre');
        pre.style.textAlign = 'left';
        pre.style.whiteSpace = 'pre-wrap';
        pre.style.maxHeight = '300px';
        pre.style.overflowY = 'auto';
        pre.textContent = p.sourceContext;

        Swal.fire({
            titleText: `${p.sourceType === 'url' ? '🔗' : '📄'} ${p.sourceName}`,
            html: pre,
            confirmButtonText: 'Close',
        });
    };

    if (deptLoading || fieldsLoading || tagsLoading || keysLoading || promptsLoading) {
        return <div className="managePanel w-100 d-flex justify-content-center"><Loading /></div>;
    }

    return (
        <div className="managePanel w-100">
            <h3 className="cardTitle" style={{ marginBottom: 'var(--space-6)' }}>Manage</h3>

            <div className="statCardsRow">
                <div className="statCard">
                    <div className="statCardNumber">{departments.length}</div>
                    <div className="statCardLabel">Departments</div>
                </div>
                <div className="statCard">
                    <div className="statCardNumber">{customFields.length}</div>
                    <div className="statCardLabel">Custom fields</div>
                </div>
                <div className="statCard">
                    <div className="statCardNumber">{tags.length}</div>
                    <div className="statCardLabel">Tags</div>
                </div>
                <div className="statCard">
                    <div className="statCardNumber">{prompts.length}</div>
                    <div className="statCardLabel">Prompts</div>
                </div>
                <div className="statCard">
                    <div className="statCardNumber">{apiKeys.length}</div>
                    <div className="statCardLabel">API keys</div>
                </div>
            </div>

            <div className="card">
                <h5 className="cardTitle">Departments</h5>
                {departments.length === 0 ? (
                    <div className="cardEmptyState">No departments yet</div>
                ) : (
                    <ul className="manageList">
                        {departments.map((d) => (
                            <li key={d._id} className="d-flex justify-content-between align-items-center">
                                <span>{d.name}</span>
                                <button type="button" className="btn-ghost" onClick={() => handleDeleteDepartment(d._id, d.name)}>✕</button>
                            </li>
                        ))}
                    </ul>
                )}
                <form className="manageForm formGroup d-flex gap-2" onSubmit={handleAddDepartment}>
                    <input
                        type="text"
                        required
                        placeholder="Department name"
                        value={deptName}
                        onChange={(e) => setDeptName(e.target.value)}
                    />
                    <button className="btn-primary" type="submit">Add department</button>
                </form>
            </div>

            <div className="card">
                <h5 className="cardTitle">Custom Fields</h5>
                {customFields.length === 0 ? (
                    <div className="cardEmptyState">No custom fields yet</div>
                ) : (
                    <ul className="manageList">
                        {customFields.map((f) => (
                            <li key={f._id} className="d-flex justify-content-between align-items-center">
                                <span>{f.name} <span className={`pill ${FIELD_TYPE_PILL[f.fieldType] || 'pill--info'}`}>{f.fieldType}{f.options ? `: ${f.options.join(', ')}` : ''}</span></span>
                                <button type="button" className="btn-ghost" onClick={() => handleDeleteField(f._id, f.name)}>✕</button>
                            </li>
                        ))}
                    </ul>
                )}
                <form className="manageForm formGroup d-flex gap-2" onSubmit={handleAddField}>
                    <input
                        type="text"
                        required
                        placeholder="Field name"
                        value={fieldName}
                        onChange={(e) => setFieldName(e.target.value)}
                    />
                    <select value={fieldType} onChange={(e) => setFieldType(e.target.value)}>
                        {FIELD_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                    {fieldType === 'select' && (
                        <input
                            type="text"
                            placeholder="Options, comma separated"
                            value={fieldOptions}
                            onChange={(e) => setFieldOptions(e.target.value)}
                        />
                    )}
                    <button className="btn-primary" type="submit">Add field</button>
                </form>
            </div>

            <div className="card">
                <h5 className="cardTitle">Tags</h5>
                {tags.length === 0 ? (
                    <div className="cardEmptyState">No tags yet</div>
                ) : (
                    <ul className="manageList">
                        {tags.map((t) => (
                            <li key={t._id} className="d-flex justify-content-between align-items-center">
                                <span>{t.name}</span>
                                <button type="button" className="btn-ghost" onClick={() => handleDeleteTag(t._id, t.name)}>✕</button>
                            </li>
                        ))}
                    </ul>
                )}
                <form className="manageForm formGroup d-flex gap-2" onSubmit={handleAddTag}>
                    <input
                        type="text"
                        required
                        placeholder="Tag name"
                        value={tagName}
                        onChange={(e) => setTagName(e.target.value)}
                    />
                    <button className="btn-primary" type="submit">Add tag</button>
                </form>
            </div>

            <div className="card">
                <h5 className="cardTitle">API Keys</h5>
                {apiKeys.length === 0 ? (
                    <div className="cardEmptyState">No API keys yet</div>
                ) : (
                    <ul className="manageList">
                        {apiKeys.map((k) => (
                            <li key={k._id} className="d-flex justify-content-between align-items-center">
                                <span>
                                    {k.name} <span className="pill pill--info">{k.keyPrefix}...</span>{' '}
                                    <span className="pill pill--warning">{k.scopesLabel}</span>
                                </span>
                                <button type="button" className="btn-ghost" onClick={() => handleRevokeApiKey(k._id, k.name)}>✕</button>
                            </li>
                        ))}
                    </ul>
                )}
                <form className="manageForm formGroup" onSubmit={handleAddApiKey}>
                    <div className="d-flex gap-2">
                        <input
                            type="text"
                            required
                            placeholder="Key name (e.g. Zapier integration)"
                            value={apiKeyName}
                            onChange={(e) => setApiKeyName(e.target.value)}
                        />
                        <button className="btn-primary" type="submit">Create key</button>
                    </div>
                    <div className="d-flex gap-3 mt-2" style={{ fontSize: 'var(--font-sm)' }}>
                        <label className="d-flex align-items-center gap-1">
                            <input
                                type="checkbox"
                                checked={apiKeyScopeRead}
                                onChange={(e) => setApiKeyScopeRead(e.target.checked)}
                            />
                            Read prompts, tags, and departments
                        </label>
                        <label className="d-flex align-items-center gap-1">
                            <input
                                type="checkbox"
                                checked={apiKeyScopeGenerate}
                                onChange={(e) => setApiKeyScopeGenerate(e.target.checked)}
                            />
                            Generate prompts (uses AI credits)
                        </label>
                    </div>
                </form>

                <div className="mcpConnectorInfo">
                    <div className="mcpConnectorLabel">MCP connector URL</div>
                    <div className="d-flex gap-2 align-items-center">
                        <code className="mcpConnectorUrl">{mcpUrl}</code>
                        <button type="button" className="btn-secondary" onClick={handleCopyMcpUrl}>Copy</button>
                    </div>
                    <p className="helperText">
                        Point an MCP-compatible client (Claude Code, Claude Desktop, Cursor, Windsurf, VS Code)
                        at this URL with one of the API keys above as a Bearer token. This is not a one-click
                        connector inside claude.ai's own UI — that specifically requires OAuth, which isn't
                        supported yet. Any client that lets you set a custom header works today.
                    </p>
                </div>

                <div className="mcpConnectorInfo">
                    <div className="mcpConnectorLabel">REST API — regenerate a saved prompt</div>
                    <p className="helperText">
                        Swap <code>PROMPT_ID</code> for a prompt's ID (visible in its share link) and
                        <code> YOUR_API_KEY</code> for one of the keys above.
                    </p>
                    <div className="d-flex justify-content-between align-items-start gap-2">
                        <pre className="codeSnippet"><code>{curlSnippet}</code></pre>
                        <button type="button" className="btn-secondary" onClick={() => handleCopySnippet(curlSnippet)}>Copy</button>
                    </div>
                    <div className="d-flex justify-content-between align-items-start gap-2 mt-2">
                        <pre className="codeSnippet"><code>{jsSnippet}</code></pre>
                        <button type="button" className="btn-secondary" onClick={() => handleCopySnippet(jsSnippet)}>Copy</button>
                    </div>
                </div>
            </div>

            <div className="card">
                <h5 className="cardTitle">
                    All Prompts
                    {prompts.length > 0 && (
                        <span className="statusBreakdown">
                            {' — '}
                            {STATUSES.map((s) => `${prompts.filter((p) => p.status === s).length} ${s}`).join(', ')}
                        </span>
                    )}
                </h5>
                {prompts.length === 0 ? (
                    <div className="cardEmptyState">No prompts yet</div>
                ) : (
                    <div className="manageTableWrap">
                        <table className="manageTable w-100">
                            <thead>
                                <tr>
                                    <th>Prompt</th>
                                    <th className="col-secondary">Category</th>
                                    <th>Status</th>
                                    <th className="col-tertiary">Rating</th>
                                    <th className="col-secondary">Department</th>
                                    <th className="col-secondary">Tags</th>
                                    {customFields.map((f) => <th key={f._id} className="col-tertiary">{f.name}</th>)}
                                    <th className="col-actions"></th>
                                </tr>
                            </thead>
                            <tbody>
                                {prompts.map((p) => (
                                    <tr key={p._id}>
                                        <td className="promptCell" title={p.userPrompt}>{p.userPrompt}</td>
                                        <td className="col-secondary">{p.category}</td>
                                        <td>
                                            <select
                                                value={p.status || 'approved'}
                                                onChange={(e) => handleStatusChange(p._id, e.target.value)}
                                            >
                                                {STATUSES.map((s) => (
                                                    <option
                                                        key={s}
                                                        value={s}
                                                        disabled={!isAdmin && (s === 'approved' || s === 'archived')}
                                                    >
                                                        {STATUS_LABEL[s]}
                                                    </option>
                                                ))}
                                            </select>
                                        </td>
                                        <td className="col-tertiary">
                                            {p.ratingCount > 0 ? `★ ${p.avgRating} (${p.ratingCount})` : '—'}
                                        </td>
                                        <td className="col-secondary">
                                            <select
                                                value={p.departmentId || ''}
                                                onChange={(e) => handleDepartmentAssign(p._id, e.target.value)}
                                            >
                                                <option value="">Unassigned</option>
                                                {departments.map((d) => (
                                                    <option key={d._id} value={d._id}>{d.name}</option>
                                                ))}
                                            </select>
                                        </td>
                                        <td className="col-secondary">
                                            <select
                                                multiple
                                                className="tagsMultiSelect"
                                                value={p.tags || []}
                                                onChange={(e) => handleTagsChange(
                                                    p._id,
                                                    Array.from(e.target.selectedOptions).map((o) => o.value)
                                                )}
                                            >
                                                {tags.map((t) => (
                                                    <option key={t._id} value={t._id}>{t.name}</option>
                                                ))}
                                            </select>
                                        </td>
                                        {customFields.map((f) => (
                                            <td key={f._id} className="col-tertiary">
                                                {f.fieldType === 'select' ? (
                                                    <select
                                                        defaultValue={p.customFields?.[f._id] || ''}
                                                        onChange={(e) => handleFieldValueChange(p._id, f._id, e.target.value)}
                                                    >
                                                        <option value=""></option>
                                                        {(f.options || []).map((o) => <option key={o} value={o}>{o}</option>)}
                                                    </select>
                                                ) : (
                                                    <input
                                                        type={f.fieldType === 'number' ? 'number' : f.fieldType === 'date' ? 'date' : 'text'}
                                                        defaultValue={p.customFields?.[f._id] || ''}
                                                        onBlur={(e) => handleFieldValueChange(p._id, f._id, e.target.value)}
                                                    />
                                                )}
                                            </td>
                                        ))}
                                        <td className="col-actions d-flex gap-1">
                                            {p.sourceContext && (
                                                <button type="button" className="btn-ghost" title={`Grounded in: ${p.sourceName}`} onClick={() => handleShowSource(p)}>
                                                    {p.sourceType === 'url' ? '🔗' : '📄'}
                                                </button>
                                            )}
                                            <button type="button" className="btn-ghost" title="History" onClick={() => handleShowHistory(p._id)}>🕘</button>
                                            <button type="button" className="btn-ghost" title="Share" onClick={() => handleShare(p._id)}>🔗</button>
                                            <button type="button" className="btn-ghost" title="Delete" onClick={() => handleDeletePrompt(p._id, p.userPrompt)}>✕</button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
            <VersionHistoryModal
                show={showVersionHistory}
                onClose={() => setShowVersionHistory(false)}
                promptId={historyPromptId}
                currentPrompt={prompts.find((p) => p._id === historyPromptId) || {}}
                versions={historyVersions}
            />
        </div>
    )
}

export default ManagePanel
