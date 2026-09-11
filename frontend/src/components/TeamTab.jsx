import React from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { setMainComponent, selectMainComponent } from '../store/slices/truPromptSlice'

const TeamTab = () => {

    const dispatch = useDispatch()
    const mainComponent = useSelector(selectMainComponent);
    const isActive = mainComponent === 'team';

    const handleTeamClick = (e) => {
        e.preventDefault();
        dispatch(setMainComponent('team'));
    }

    return (
        <div className={`historyDiv navItem w-100 ${isActive ? 'navItem--active' : ''}`}>
            <h5
                className="mb-0 SideBarTitle"
                role='button' data-bs-dismiss={window.innerWidth < 768 ? "offcanvas" : ''}
                onClick={(e) => { handleTeamClick(e) }}>
                Team
            </h5>
        </div>
    )
}

export default TeamTab
