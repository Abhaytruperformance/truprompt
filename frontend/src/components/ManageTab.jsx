import React from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { setMainComponent, selectMainComponent } from '../store/slices/truPromptSlice'
import { useGetMyOrgQuery } from '../store/slices/orgSlice'

const ManageTab = () => {
    const dispatch = useDispatch()
    const { data: orgData } = useGetMyOrgQuery();
    const isAdmin = orgData?.role === 'admin' || orgData?.role === 'owner';
    const mainComponent = useSelector(selectMainComponent);
    const isActive = mainComponent === 'manage';

    if (!isAdmin) return null;

    const handleManageClick = (e) => {
        e.preventDefault();
        dispatch(setMainComponent('manage'));
    }

    return (
        <div className={`historyDiv navItem w-100 ${isActive ? 'navItem--active' : ''}`}>
            <h5
                className="mb-0 SideBarTitle"
                role='button' data-bs-dismiss={window.innerWidth < 768 ? "offcanvas" : ''}
                onClick={(e) => { handleManageClick(e) }}>
                Manage
            </h5>
        </div>
    )
}

export default ManageTab
