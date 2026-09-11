import React from 'react'
import HistoryIcon from '../assets/History.svg'
import { useDispatch } from 'react-redux'
import { setMainComponent, setPromptSource } from '../store/slices/truPromptSlice'


const History = () => {

    const dispatch = useDispatch()

    const handleHistory = (e) => {
        e.preventDefault();
        dispatch(setPromptSource('openAIPrompts'))
        dispatch(setMainComponent('History'));
    }

    return (
        <>
            <div className='historyDiv w-100'>

                <h5
                    className="mb-0 SideBarTitle"
                    role='button' data-bs-dismiss={window.innerWidth < 768 ? "offcanvas" : ''}
                    onClick={(e) => { handleHistory(e) }}>
                    <img src={HistoryIcon} alt='History' width={18} height={18} style={{ marginRight: '8px' }} />
                    History
                </h5>
            </div>
        </>
    )
}

export default History