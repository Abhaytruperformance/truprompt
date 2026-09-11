import React, { useState } from 'react'
import './CSS/MainComponent.css'
import TopPromptSuggestions from './TopPromptSuggestions'
import HandlePrompt from './HandlePrompt'
import { useSelector } from 'react-redux'
import { selectIsDropdownOpen } from '../store/slices/truPromptSlice'

const NewChat = ({ userData, setLoading, selectedOptions, openAIResults, setSelectedOptions, setOpenAIResults }) => {
    const isDropdownOpen = useSelector(selectIsDropdownOpen)
    // const [isBlur, setIsBlur] = useState(false);
    // const [isDropdownOpen, setIsDropdownOpen] = useState(false);
    // const dropdownRef = useRef(null);
    const [prompt, setPrompt] = useState("");

    // const handleClickOutside = (event) => {
    //     if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
    //         setIsDropdownOpen(false);
    //         // setIsBlur(!isBlur)
    //     }
    // };



    return (
        <>
            <div className={`mainComponentContainer`} >

                <div >
                    <div className={`${isDropdownOpen ? 'isBlur' : ''}`} >
                        <div className="userDiv">
                            <h2 className='userName'>Hi, {userData.name}</h2>
                            <p className='subTitle'>I can generate and optimize prompts, What are you creating today?</p>
                        </div>
                        <TopPromptSuggestions
                            prompt={prompt}
                            setPrompt={setPrompt}
                            // mainComponent={mainComponent}
                            setLoading={setLoading}
                            selectedOptions={selectedOptions}
                            openAIResults={openAIResults}
                            setSelectedOptions={setSelectedOptions}
                            setOpenAIResults={setOpenAIResults}
                        />

                    </div>
                    {/* <UserInput /> */}
                    <HandlePrompt
                        prompt={prompt}
                        setPrompt={setPrompt}
                        setLoading={setLoading}
                        selectedOptions={selectedOptions}
                        openAIResults={openAIResults}
                        setSelectedOptions={setSelectedOptions}
                        setOpenAIResults={setOpenAIResults}
                    // isDropdownOpen={isDropdownOpen}
                    // setIsDropdownOpen={setIsDropdownOpen}
                    // dropdownRef={dropdownRef}
                    // mainComponent={mainComponent}

                    />
                </div>
            </div >
        </>
    )
}

export default NewChat