import React, { useState } from 'react'
import Swal from 'sweetalert2'
import {
    useGetMyOrgQuery,
    useGetMembersQuery,
    useUpdateMemberRoleMutation,
    useGetInvitationsQuery,
    useInviteMemberMutation,
    useCancelInvitationMutation,
    useUpdateWorkosConnectionMutation,
} from '../store/slices/orgSlice'
import Loading from './Loading'
import './CSS/TeamPanel.css'

const ROLES = ['member', 'editor', 'admin', 'owner'];
const ROLE_PILL = { owner: 'pill--danger', admin: 'pill--warning', editor: 'pill--info', member: 'pill--success' };

const showToast = (title) => {
    Swal.fire({ toast: true, position: 'top-end', showConfirmButton: false, timer: 2000, icon: 'success', title });
};

const showError = (title, err) => {
    Swal.fire({ icon: 'error', title, text: err?.data?.detail || 'Something went wrong' });
};

const TeamPanel = () => {
    const { data: orgData, isLoading: orgLoading } = useGetMyOrgQuery();
    const { data: members = [], isLoading: membersLoading } = useGetMembersQuery();
    const isAdmin = orgData?.role === 'admin' || orgData?.role === 'owner';
    const { data: invitations = [] } = useGetInvitationsQuery(undefined, { skip: !isAdmin });

    const [updateMemberRole] = useUpdateMemberRoleMutation();
    const [inviteMember] = useInviteMemberMutation();
    const [cancelInvitation] = useCancelInvitationMutation();
    const [updateWorkosConnection] = useUpdateWorkosConnectionMutation();

    const [inviteEmail, setInviteEmail] = useState('');
    const [inviteRole, setInviteRole] = useState('member');
    const [newConnectionId, setNewConnectionId] = useState('');

    const handleRoleChange = async (userId, role) => {
        try {
            await updateMemberRole({ userId, role }).unwrap();
            showToast('Role updated');
        } catch (err) {
            showError('Could not update role', err);
        }
    };

    const handleCancelInvitation = async (id, email) => {
        const confirm = await Swal.fire({
            icon: 'warning',
            title: 'Cancel this invitation?',
            text: email,
            showCancelButton: true,
            confirmButtonText: 'Cancel invitation',
        });
        if (!confirm.isConfirmed) return;
        try {
            await cancelInvitation(id).unwrap();
            showToast('Invitation cancelled');
        } catch (err) {
            showError('Could not cancel invitation', err);
        }
    };

    const handleInvite = async (e) => {
        e.preventDefault();
        try {
            await inviteMember({ email: inviteEmail, role: inviteRole }).unwrap();
            showToast('Invitation sent');
            setInviteEmail('');
        } catch (err) {
            showError('Could not send invite', err);
        }
    };

    const handleSaveConnection = async (e) => {
        e.preventDefault();
        try {
            await updateWorkosConnection(newConnectionId).unwrap();
            showToast('SSO connection saved');
            setNewConnectionId('');
        } catch (err) {
            showError('Could not save SSO connection', err);
        }
    };

    const handleRemoveConnection = async () => {
        const confirm = await Swal.fire({
            icon: 'warning',
            title: 'Remove the SSO connection?',
            text: 'Members will no longer be able to log in via company SSO.',
            showCancelButton: true,
            confirmButtonText: 'Remove',
        });
        if (!confirm.isConfirmed) return;
        try {
            await updateWorkosConnection(null).unwrap();
            showToast('SSO connection removed');
        } catch (err) {
            showError('Could not remove SSO connection', err);
        }
    };

    const handleCopyLoginLink = async (slug) => {
        const link = `${window.location.origin}/?org=${slug}`;
        if (navigator.clipboard) await navigator.clipboard.writeText(link);
        showToast('Login link copied');
    };

    if (orgLoading || membersLoading) {
        return <div className="teamPanel w-100 d-flex justify-content-center"><Loading /></div>;
    }

    const adminCount = members.filter((m) => m.role === 'admin' || m.role === 'owner').length;

    return (
        <div className="teamPanel w-100">
            <h3 className="cardTitle" style={{ marginBottom: 4 }}>{orgData?.organization?.name || 'Organization'}</h3>
            <p className="teamPanelRole">Your role: {orgData?.role}</p>

            <div className="statCardsRow">
                <div className="statCard">
                    <div className="statCardNumber">{members.length}</div>
                    <div className="statCardLabel">Members</div>
                </div>
                {isAdmin && (
                    <>
                        <div className="statCard">
                            <div className="statCardNumber">{invitations.length}</div>
                            <div className="statCardLabel">Pending invitations</div>
                        </div>
                        <div className="statCard">
                            <div className="statCardNumber">{adminCount}</div>
                            <div className="statCardLabel">Admins+</div>
                        </div>
                    </>
                )}
            </div>

            <div className="card">
                <h5 className="cardTitle">Members</h5>
                {members.length === 0 ? (
                    <div className="cardEmptyState">No members yet</div>
                ) : (
                    <table className="teamTable w-100">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Email</th>
                                <th>Role</th>
                            </tr>
                        </thead>
                        <tbody>
                            {members.map((m) => (
                                <tr key={m._id}>
                                    <td>{m.name}</td>
                                    <td>{m.email}</td>
                                    <td>
                                        {isAdmin ? (
                                            <select
                                                value={m.role}
                                                onChange={(e) => handleRoleChange(m.userId, e.target.value)}
                                            >
                                                {ROLES.map((r) => (
                                                    <option key={r} value={r}>{r}</option>
                                                ))}
                                            </select>
                                        ) : (
                                            <span className={`pill ${ROLE_PILL[m.role] || 'pill--info'}`}>{m.role}</span>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

            {isAdmin && (
                <>
                    <div className="card card--compact">
                        <h5 className="cardTitle">Invite a teammate</h5>
                        <form className="inviteForm d-flex gap-2" onSubmit={handleInvite}>
                            <input
                                type="email"
                                required
                                placeholder="email@example.com"
                                value={inviteEmail}
                                onChange={(e) => setInviteEmail(e.target.value)}
                            />
                            <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}>
                                {ROLES.map((r) => (
                                    <option key={r} value={r}>{r}</option>
                                ))}
                            </select>
                            <button className="btn-primary" type="submit">Invite</button>
                        </form>
                    </div>

                    <div className="card">
                        <h5 className="cardTitle">Pending invitations</h5>
                        {invitations.length === 0 ? (
                            <div className="cardEmptyState">No pending invitations</div>
                        ) : (
                            <ul className="inviteList">
                                {invitations.map((inv) => (
                                    <li key={inv._id} className="d-flex justify-content-between align-items-center">
                                        <span>{inv.email} — <span className={`pill ${ROLE_PILL[inv.role] || 'pill--info'}`}>{inv.role}</span></span>
                                        <button
                                            type="button"
                                            className="btn-ghost"
                                            title="Cancel invitation"
                                            onClick={() => handleCancelInvitation(inv._id, inv.email)}
                                        >
                                            ✕
                                        </button>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>

                    <div className="card card--compact">
                        <h5 className="cardTitle">Single Sign-On</h5>
                        {orgData?.organization?.workosConnectionId ? (
                            <>
                                <p className="helperText">SSO is configured for this organization.</p>
                                <div className="d-flex gap-2 align-items-center mb-3">
                                    <code className="mcpConnectorUrl">{`${window.location.origin}/?org=${orgData.organization.slug}`}</code>
                                    <button type="button" className="btn-secondary" onClick={() => handleCopyLoginLink(orgData.organization.slug)}>Copy login link</button>
                                    <button type="button" className="btn-danger" onClick={handleRemoveConnection}>Remove</button>
                                </div>
                            </>
                        ) : (
                            <p className="helperText">
                                Not configured yet. Set up your identity provider (Okta/Azure AD/Google Workspace)
                                in your WorkOS dashboard first, then paste the resulting connection id below.
                            </p>
                        )}
                        <form className="inviteForm d-flex gap-2" onSubmit={handleSaveConnection}>
                            <input
                                type="text"
                                required
                                placeholder="conn_..."
                                value={newConnectionId}
                                onChange={(e) => setNewConnectionId(e.target.value)}
                            />
                            <button className="btn-primary" type="submit">Save connection</button>
                        </form>
                    </div>
                </>
            )}
        </div>
    )
}

export default TeamPanel
