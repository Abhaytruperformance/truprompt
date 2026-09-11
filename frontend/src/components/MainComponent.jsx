import React from 'react'
import NewChat from './NewChat'
import PromptResults from './PromptResults'
import { useSelector } from 'react-redux';
import { selectMainComponent, selectPromptId, selectPromptSource, useGetSinglePromptQuery } from '../store/slices/truPromptSlice';
import HandlePrompt from './HandlePrompt';
import TeamPanel from './TeamPanel';
import ManagePanel from './ManagePanel';
import Playground from './Playground';
import Analytics from './Analytics';

const MainComponent = ({ loading, prompt, setPrompt, userData, setLoading, selectedOptions, openAIResults, setSelectedOptions, setOpenAIResults }) => {

    const Results = useSelector(selectPromptSource);
    const promptId = useSelector(selectPromptId);
    const mainComponent = useSelector(selectMainComponent);
    const { data: singlePrompt, } = useGetSinglePromptQuery(promptId, {
        skip: !promptId,
    });

    return (
        <>
            <div
                key={mainComponent}
                className={`mainComponent panelEnter d-flex flex-column align-items-center ${(Results === 'singlePrompt' || mainComponent !== 'History') ? 'singlePrompt' : 'AllPrompts'}`}
            >
                {mainComponent === 'team' ? (
                    <TeamPanel />
                ) : mainComponent === 'manage' ? (
                    <ManagePanel />
                ) : mainComponent === 'playground' ? (
                    <Playground />
                ) : mainComponent === 'analytics' ? (
                    <Analytics />
                ) : mainComponent === 'newChat' ? (
                    <NewChat
                        userData={userData}
                        setLoading={setLoading}
                        selectedOptions={selectedOptions}
                        openAIResults={openAIResults}
                        setSelectedOptions={setSelectedOptions}
                        setOpenAIResults={setOpenAIResults}
                    // mainComponent={mainComponent}
                    />
                ) : (
                    <>
                        <PromptResults
                            loading={loading}
                            prompts={(Results === 'openAIPrompts') ? openAIResults : singlePrompt || []}
                            setPrompt={setPrompt}
                            promptFromDB={(Results === 'singlePrompt') ? true : false}
                            setLoading={setLoading}
                            setOpenAIResults={setOpenAIResults}
                            setSelectedOptions={setSelectedOptions}
                            selectedOptions={selectedOptions}

                        />
                        {mainComponent !== 'History' && (
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
                        )}

                    </>

                )}
            </div >
        </>
    )
}

export default MainComponent