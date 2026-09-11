import React from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { setMainComponent, selectMainComponent } from '../store/slices/truPromptSlice'
import { useGetMyOrgQuery } from '../store/slices/orgSlice'

const AnalyticsTab = () => {
    const dispatch = useDispatch()
    const { data: orgData } = useGetMyOrgQuery();
    const isAdmin = orgData?.role === 'admin' || orgData?.role === 'owner';
    const mainComponent = useSelector(selectMainComponent);
    const isActive = mainComponent === 'analytics';

    if (!isAdmin) return null;

    const handleAnalyticsClick = (e) => {
        e.preventDefault();
        dispatch(setMainComponent('analytics'));
    }

    return (
        <div className={`historyDiv navItem w-100 ${isActive ? 'navItem--active' : ''}`}>
            <h5
                className="mb-0 SideBarTitle"
                role='button' data-bs-dismiss={window.innerWidth < 768 ? "offcanvas" : ''}
                onClick={(e) => { handleAnalyticsClick(e) }}>
                Analytics
            </h5>
        </div>
    )
}

export default AnalyticsTab
