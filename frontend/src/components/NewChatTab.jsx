import React from 'react'
import { useDispatch, useSelector } from 'react-redux';
import newChatIcon from '../assets/newChatIcon.svg'
import { setMainComponent, setPromptSource, selectMainComponent } from '../store/slices/truPromptSlice'


const NewChatTab = () => {

    const dispatch = useDispatch();
    const mainComponent = useSelector(selectMainComponent);
    const isActive = mainComponent === 'newChat';

    const handleNewChatClick = (e) => {
        e.preventDefault();
        dispatch(setMainComponent('newChat'));
        dispatch(setPromptSource('singlePrompt'));
    }

    return (
        <div
            className={`newChatDiv navItem d-flex justify-content-between w-100 ${isActive ? 'navItem--active' : ''}`}
            role='button'
            data-bs-dismiss={window.innerWidth < 768 ? "offcanvas" : ''}
            onClick={(e) => handleNewChatClick(e)}>
            <p className='newChatText'>New Chat</p>
            <img src={newChatIcon} alt="New Chat" width={24} height={24} />
        </div>
    )
}

export default NewChatTab