import React from 'react'
import { setMainComponent, setPromptId, setPromptSource, useGetPromptsQuery } from '../store/slices/truPromptSlice';
import { useDispatch } from 'react-redux';


const TopPromptSuggestions = ({
    prompt,
    setPrompt,
    setLoading,
    selectedOptions,
    setSelectedOptions,
    openAIResults,
    setOpenAIResults,
}) => {

    const dispatch = useDispatch();


    const { data: prompts = [] } = useGetPromptsQuery();

    // Most Used Prompt sorted
    const sortedPrompts = [...prompts]?.sort((a, b) => {
        return b.mostUsedPromptCount - a.mostUsedPromptCount;
    })


    // Display only the first 4 sorted prompts
    const topFourPrompts = sortedPrompts.slice(0, 4).map((prompt, index) => (
        <div
            key={index} // Use a unique key if available
            className="topPromptCard"
            role='button'
            onClick={(e) => { handlePromptSearch(e, prompt._id) }} // Pass the prompt to the function
        >
            <h6 className='topPromptFunction'>{prompt.category}</h6>
            <p className='topPrompt'>{prompt.userPrompt}</p>
        </div>
    ));

    const handlePromptSearch = (e, promptId) => {
        e.preventDefault();
        // MainComponent('')

        dispatch(setMainComponent('promptResult'));
        dispatch(setPromptId(promptId));
        dispatch(setPromptSource('singlePrompt')); // Set source to singlePrompt
    }

    return (
        <div className="topPromptsDiv">
            <h5 className='topPromptTitle'>Top Prompt Suggestions</h5>
            <div className="topPromptCardsDiv d-flex flex-column flex-sm-row gap-4">

                {/* <div
                    className="topPromptCard"
                    role='button'
                    onClick={(e) => { generateTopPrompt(e, '') }}
                >
                    <h6 className='topPromptFunction'>Content Creation</h6>
                    <p className='topPrompt'>How to dominate search rankings with AI-driven content clusters.</p>
                </div>
                <div className="topPromptCard" role='button'>
                    <h6 className='topPromptFunction'>Design</h6>
                    <p className='topPrompt'>Design a futuristic interface for an AI-based app.</p>
                </div>
                <div className="topPromptCard" role='button'>
                    <h6 className='topPromptFunction'>Lead Generation</h6>
                    <p className='topPrompt'>Write a lead magnet that uses AI-generated personalized recommendations.</p>
                </div>
                <div className="topPromptCard" role='button'>
                    <h6 className='topPromptFunction'>Business Development</h6>
                    <p className='topPrompt'>Identify profitable niches in the [industry] for the next quarter.</p>
                </div> */}
                {topFourPrompts}
            </div>
        </div>
    )
}

export default TopPromptSuggestions