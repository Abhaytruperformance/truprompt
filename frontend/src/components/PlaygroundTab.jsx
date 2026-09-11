import React from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { setMainComponent, selectMainComponent } from '../store/slices/truPromptSlice'

const PlaygroundTab = () => {

    const dispatch = useDispatch()
    const mainComponent = useSelector(selectMainComponent);
    const isActive = mainComponent === 'playground';

    const handlePlaygroundClick = (e) => {
        e.preventDefault();
        dispatch(setMainComponent('playground'));
    }

    return (
        <div className={`historyDiv navItem w-100 ${isActive ? 'navItem--active' : ''}`}>
            <h5
                className="mb-0 SideBarTitle"
                role='button' data-bs-dismiss={window.innerWidth < 768 ? "offcanvas" : ''}
                onClick={(e) => { handlePlaygroundClick(e) }}>
                Playground
            </h5>
        </div>
    )
}

export default PlaygroundTab
