import React, { useState } from 'react'
import { setIsDropdownOpen, setMainComponent, setPromptSource, useGetAuthPromptsQuery, useGetPromptsQuery } from "../store/slices/truPromptSlice";
import { useDispatch } from 'react-redux';
import { setPromptId } from '../store/slices/truPromptSlice';
import { useAllUsersQuery } from '../store/slices/authSlice';
import { useGetDepartmentsQuery, useGetTagsQuery } from '../store/slices/orgSlice';
import Loading from './Loading'
import savedPrompt from '../assets/savedPrompt.svg'
import mostUsedPromptIcon from '../assets/mostUsedPromptIcon.svg'

const STATUS_PILL = { draft: 'pill--info', review: 'pill--warning', approved: 'pill--success', archived: 'pill--danger' };
const STATUS_LABEL = { draft: 'Draft', review: 'Review', approved: '✓ Approved', archived: 'Archived' };

const GetPrompts = ({ auth, accordian }) => {

    const { isLoading: usersLoading } = useAllUsersQuery();


    const dispatch = useDispatch();

    const [search, setSearch] = useState('');
    const [departmentFilter, setDepartmentFilter] = useState('');
    const [tagFilter, setTagFilter] = useState('');
    const [statusFilter, setStatusFilter] = useState('');
    const filters = { search, departmentId: departmentFilter, tagId: tagFilter, status: statusFilter };

    const { data: prompts = [] } = useGetAuthPromptsQuery(filters);
    const { data: allprompts = [] } = useGetPromptsQuery(filters);
    const { data: departments = [] } = useGetDepartmentsQuery();
    const { data: tags = [] } = useGetTagsQuery();




    const handlePromptSearch = (e, promptId) => {
        e.preventDefault();
        dispatch(setMainComponent('promptResult'));
        dispatch(setPromptId(promptId));
        dispatch(setPromptSource('singlePrompt')); // Set source to singlePrompt
        dispatch(setIsDropdownOpen(false));
    }

    // Assuming prompts is an array of objects as shown in the image
    const sortedPrompts = [...(auth ? prompts : allprompts)].sort((a, b) => {
        if (auth) {
            // Sort by updatedAt in descending order if auth is true
            return new Date(b.updatedAt) - new Date(a.updatedAt);
        } else {
            // Sort by mostUsedPromptCount in descending order if auth is false
            return b.mostUsedPromptCount - a.mostUsedPromptCount;
        }
    });

    // Group by department only for "My Saved Prompts" -- the org-wide "Most
    // Used" list stays flat since department grouping doesn't serve a
    // popularity ranking the same way.
    const groupedByDepartment = auth
        ? sortedPrompts.reduce((acc, p) => {
            const key = departments.find((d) => d._id === p.departmentId)?.name || 'Unassigned';
            (acc[key] = acc[key] || []).push(p);
            return acc;
        }, {})
        : null;

    if (usersLoading) {
        return <Loading />
    }

    return (
        <div className="tab w-100">
            <div className="">
                <div className='accordion-header mb-0'>
                    <div className={`accordion-button ${!auth ? '' : 'collapsed'}`} type="button" data-bs-toggle="collapse" data-bs-target={auth ? '#mySavedPrompts' : '#mostUsedPrompts'} aria-expanded="true" aria-controls={auth ? 'mySavedPrompts' : 'mostUsedPrompts'}>
                        {auth && <h5 className="mb-0 SideBarTitle"><img src={savedPrompt} alt='Saved Prompt' style={{ marginRight: "8px" }} />My Saved Prompts</h5>}
                        {!auth && <h5 className="mb-0 SideBarTitle"><img src={mostUsedPromptIcon} alt='Most Used Prompt' style={{ marginRight: "8px" }} />Most Used Prompts</h5>}
                    </div>
                </div>
                <div id={auth ? 'mySavedPrompts' : 'mostUsedPrompts'} className={`accordion-collapse collapse ${!auth ? 'show' : ''}`} data-bs-parent={`#promptsAccordian${accordian}`}>
                    <div className="accordion-body">
                        <div className="promptFilters d-flex flex-column gap-1 mb-2">
                            <input
                                type="text"
                                className="promptSearchInput"
                                placeholder="Search prompts..."
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                            />
                            <div className="d-flex gap-1">
                                <select value={departmentFilter} onChange={(e) => setDepartmentFilter(e.target.value)}>
                                    <option value="">All departments</option>
                                    {departments.map((d) => (
                                        <option key={d._id} value={d._id}>{d.name}</option>
                                    ))}
                                </select>
                                <select value={tagFilter} onChange={(e) => setTagFilter(e.target.value)}>
                                    <option value="">All tags</option>
                                    {tags.map((t) => (
                                        <option key={t._id} value={t._id}>{t.name}</option>
                                    ))}
                                </select>
                                <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                                    <option value="">{auth ? 'All statuses' : 'Approved only'}</option>
                                    <option value="draft">Draft</option>
                                    <option value="review">Review</option>
                                    <option value="approved">Approved</option>
                                    <option value="archived">Archived</option>
                                    {!auth && <option value="all">All statuses</option>}
                                </select>
                            </div>
                        </div>
                        {auth ? (
                            sortedPrompts.length > 0 ? (
                                Object.entries(groupedByDepartment).map(([deptLabel, deptPrompts]) => (
                                    <div key={deptLabel} className="departmentGroup">
                                        <h6 className="departmentGroupTitle">{deptLabel}</h6>
                                        <ul className='list-group' id="recent-saved">
                                            {deptPrompts.map((prompt, index) => (
                                                <li key={prompt._id || index} className="list-item d-flex align-items-center justify-content-between">
                                                    <div className='d-flex align-items-center'>
                                                        <button
                                                            className="btn btn-link p-0 list-item-left tgpt-list-butn"
                                                            onClick={(e) => handlePromptSearch(e, prompt._id)}
                                                            title={prompt.userPrompt}
                                                            data-bs-dismiss={window.innerWidth < 768 ? "offcanvas" : undefined}
                                                        >
                                                            {prompt.userPrompt}
                                                        </button>
                                                    </div>
                                                    <span className={`pill ${STATUS_PILL[prompt.status] || 'pill--info'}`}>{STATUS_LABEL[prompt.status] || prompt.status}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                ))
                            ) : (
                                <ul className='list-group' id="recent-saved">
                                    <li className="list-item d-flex align-items-center justify-content-between emptyList">
                                        Start creating your first prompt!
                                    </li>
                                </ul>
                            )
                        ) : (
                            <ul className='list-group' id="most-used">
                                {sortedPrompts.length > 0 ? (
                                    sortedPrompts.map((prompt, index) => (
                                        <li key={index} className="list-item d-flex align-items-center justify-content-between">
                                            <div className='d-flex align-items-center'>
                                                <button
                                                    className="btn btn-link p-0 list-item-left tgpt-list-butn"
                                                    onClick={(e) => handlePromptSearch(e, prompt._id)}
                                                    title={prompt.userPrompt}
                                                    data-bs-dismiss={window.innerWidth < 768 ? "offcanvas" : undefined}
                                                >
                                                    {prompt.userPrompt}
                                                </button>
                                            </div>
                                            <span className={`pill ${STATUS_PILL[prompt.status] || 'pill--info'}`}>{STATUS_LABEL[prompt.status] || prompt.status}</span>
                                            {prompt.mostUsedPromptCount !== 0 && (<span className="badge rounded-pill count-searches">{prompt.mostUsedPromptCount}</span>)}
                                        </li>
                                    ))
                                ) : (
                                    <li className="list-item d-flex align-items-center justify-content-between emptyList">
                                        Start creating your first prompt!
                                    </li>
                                )}
                            </ul>
                        )}
                    </div>
                </div>
            </div>

        </div >
    );


}

export default GetPrompts