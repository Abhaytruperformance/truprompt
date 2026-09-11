import React, { useState } from 'react'
import SaveModal from './SaveModal';
import Swal from 'sweetalert2';
import '@sweetalert2/theme-dark';
import Loading from './Loading'
import { selectIsDropdownOpen, selectMainComponent, selectPromptSource, useUpdatePromptCountMutation, useUpdatePromptRatingMutation } from '../store/slices/truPromptSlice';
import { handlePromptSearch } from './openAIUtils';
import { useDispatch, useSelector } from 'react-redux';
import { OverlayTrigger, Tooltip } from 'react-bootstrap';
import './CSS/promptResults.css'
import copy from '../assets/copy.svg'
import save from '../assets/save.svg'
import regenerate from '../assets/regenerate.svg'
import NoDataFound from '../assets/NoDataFound.svg'

const PromptResults = ({ prompts, setPrompt, promptFromDB, loading, setLoading, setOpenAIResults, setSelectedOptions }) => {

    const dispatch = useDispatch();
    const PromptSource = useSelector(selectPromptSource);
    const mainComponent = useSelector(selectMainComponent);
    const isDropdownOpen = useSelector(selectIsDropdownOpen);


    const [mostUsedPromptCount] = useUpdatePromptCountMutation();
    const [updatePromptRating] = useUpdatePromptRatingMutation();
    // const promptData = prompts && prompts.prompt ? prompts.prompt : null;
    // console.log(prompts);

    const [showSaveDialog, setShowSaveDialog] = useState(false);
    const [selectedPrompt, setSelectedPrompt] = useState(null);
    // const [show, setShow] = useState(false);


    const handleShow = (result) => {
        setSelectedPrompt(result); // Set the selected prompt data
        setShowSaveDialog(true); // Show the save dialog
    };

    const copyToClipboard = async (result) => {
        const textToCopy = result.prompt;


        if (navigator.clipboard) {
            navigator.clipboard.writeText(textToCopy)
                .then(() => {
                    Swal.fire({ // Show success alert
                        title: 'Success!',
                        text: 'Prompt copied to the Clipboard successfully!',
                        icon: 'success',
                        confirmButtonText: 'OK',
                        theme: 'dark'
                    })
                })
                .catch(err => {
                    Swal.fire({ // Show error alert
                        title: 'Error!',
                        text: 'Faied to Copy. Please copy manually',
                        icon: 'error',
                        confirmButtonText: 'OK',
                        theme: 'dark'
                    });
                });
        } else {
            Swal.fire({ // Show error alert
                title: 'Error!',
                text: 'Faied to Copy. Please copy manually',
                icon: 'error',
                confirmButtonText: 'OK',
                theme: 'dark'
            });
        }

        // increment the mostUsedPromptCounttry
        let copyToClipboardPromptId = result._id || result.promptDBId;

        if (copyToClipboardPromptId) {
            try {
                await mostUsedPromptCount(copyToClipboardPromptId).unwrap()
            } catch (error) {
                Swal.fire({ // Show error alert
                    title: 'Error!',
                    text: 'Unable to increment the most Used Prompt Count. Error on the server level',
                    icon: 'error',
                    confirmButtonText: 'OK',
                    theme: 'dark'
                });
                // console.log(error);
            }

        }

    };

    const handleRate = async (promptId, rating) => {
        try {
            await updatePromptRating({ id: promptId, rating }).unwrap();
        } catch (error) {
            Swal.fire({
                title: 'Error!',
                text: 'Could not save your rating.',
                icon: 'error',
                confirmButtonText: 'OK',
                theme: 'dark'
            });
        }
    };

    const regeneratePrompt = async (e, result) => {
        let prompt = result.userPrompt;
        let selectedOptions = result.category.includes(',') ? result.category.split(',') : [result.category];

        handlePromptSearch(e, prompt, setPrompt, setLoading, setOpenAIResults, selectedOptions, setSelectedOptions, dispatch)

    };

    if (loading) {
        return <Loading variant="generate" />
    }


    let promptsToDisplay;

    if (Array.isArray(prompts)) {
        promptsToDisplay = (mainComponent === 'History' && PromptSource === 'openAIPrompts')
            ? prompts.sort((a, b) => b.id - a.id) // Sort prompts if mainComponent is 'History'
            : prompts.slice(-1); // Return the last prompt otherwise
    } else {
        promptsToDisplay = []; // Fallback to an empty array if prompts is not an array
    }





    return (
        <div className={`${isDropdownOpen ? 'isBlur' : ''}`}>
            {promptFromDB ? (
                // When promptFromDB is true, display the singlePrompt
                <div className="result-container mb-4">
                    {/* <div className='mb-5 mt-1'>
                        <h6 className="bg-dark text-white p-2 rounded-top mb-0 text-center">Prompt From the Database</h6>
                    </div>
                    <h5>
                        <i className="fa fa-tags" aria-hidden="true"></i> Prompt for the Function: {prompts.category}
                    </h5> */}
                    <div className="userPromptDiv d-flex justify-content-end">
                        <p className="userPrompt"> {prompts.userPrompt}</p>

                    </div>
                    <div className="promptResultDiv">
                        <div className="">
                            <h6 className="promptResultTitle">Optimizer</h6>
                            <div className="">
                                <pre className="mb-0 promptResultContent" >{prompts.optimizer}</pre>
                            </div>
                        </div>
                        <hr className='divider' />
                        <div className="">
                            <h6 className="promptResultTitle">Prompt</h6>
                            <div className="">
                                <pre className="mb-0 promptResultContent">{prompts.prompt}</pre>
                            </div>
                        </div>
                        <div className="mt-3 button-copy">
                            {/* <button className="btn btn-primary me-2" onClick={() => handleShow(prompts)}>
                            Save
                        </button> */}
                            <div className='d-flex actionButtonDiv'>
                                <img src={copy} alt="Copy to Clipboard" width={15} height={15} title='Copy to Clipbaord' onClick={() => copyToClipboard(prompts)} role='button' />
                                <img src={regenerate} alt="Regenerate Prompt" width={15} height={15} title='Regenerate Prompt' onClick={(e) => regeneratePrompt(e, prompts)} role='button' />
                            </div>
                            {/* <button className="btn btn-secondary me-2" onClick={() => copyToClipboard(prompts)}>
                                Copy
                            </button>
                            <button
                                className={`btn btn-info regen}`}
                                onClick={(e) => regeneratePrompt(e, prompts)}
                            >Regenerate
                            </button> */}
                        </div>
                        <div className="ratingControl d-flex align-items-center gap-1 mt-3">
                            {[1, 2, 3, 4, 5].map((n) => (
                                <span
                                    key={n}
                                    role="button"
                                    className={`ratingStar ${n <= (prompts.myRating || 0) ? 'ratingStarFilled' : ''}`}
                                    onClick={() => handleRate(prompts._id, n)}
                                >★</span>
                            ))}
                            {prompts.ratingCount > 0 && (
                                <span className="ratingSummary">{prompts.avgRating} ({prompts.ratingCount})</span>
                            )}
                        </div>
                    </div>
                </div>
            ) : (
                // When promptFromDB is false, display the openAIResults
                // 
                // 
                // ADDED SLICE TO SHOW ONLY ONE PROMPT

                promptsToDisplay.length > 0 ? (
                    // .sort(Results === 'History' ? (a, b) => b.id - a.id : () => 0) // Sort if 'History', otherwise do nothing
                    // .slice(Results === 'openAIPrompts' ? -1 : 0) // Return the last prompt if 'openAIPrompts', otherwise return all
                    promptsToDisplay.map((result) => (
                        <div key={result.id} className="result-container resultEnter mb-4">
                            {/* <div className='d-flex justify-content-between align-items-center'>
                                <h5 className='w-75'>
                                    <i className="fa fa-tags" aria-hidden="true"></i> Prompt for the Function: {result.category}
                                </h5>
                                <div className='d-flex align-items-center w-25'>
                                    <img src={aiAnimation} alt="AI" width={80} />
                                    <div>
                                        <p className='m-0'>Powered by</p>
                                        <p className='m-0'>Open AI</p>

                                    </div>
                                </div>

                            </div> */}
                            <div className="userPromptDiv d-flex justify-content-end">
                                <p className="userPrompt"> {result.userPrompt}</p>

                            </div>
                            <div className="promptResultDiv">
                                <div className="">
                                    <h6 className="promptResultTitle">Optimizer</h6>
                                    <div className="">
                                        <pre className="promptResultContent">{result.optimizer}</pre>
                                    </div>
                                </div>
                                <div className="">
                                    <h6 className="promptResultTitle">Prompt</h6>
                                    <div className="">
                                        <pre className="promptResultContent" >{result.prompt}</pre>
                                    </div>
                                </div>
                                {/* <div className="mt-3 button-copy">
                                    {result.savedStatus === true ? (
                                        <OverlayTrigger
                                            placement="bottom"
                                            overlay={
                                                <Tooltip id={`tooltip-bottom`}>
                                                    Already saved into the DB
                                                </Tooltip>
                                            }
                                        >
                                            <button
                                                className="btn btn-primary me-2 "
                                            // onClick={() => handleShow(result)}
                                            // disabled
                                            >
                                                Save
                                            </button>
                                        </OverlayTrigger>
                                    ) : (
                                        <button
                                            className="btn btn-primary me-2"
                                            onClick={() => handleShow(result)}
                                        >
                                            Save
                                        </button>
                                    )}
                                    <button className="btn btn-secondary me-2" onClick={() => copyToClipboard(result)}>
                                        Copy
                                    </button>
                                    <button
                                        className={`btn btn-info regen}`}
                                        onClick={(e) => regeneratePrompt(e, result)}
                                    >Regenerate
                                    </button>
                                </div> */}
                                <div className='d-flex actionButtonDiv'>
                                    <img src={copy} alt="Copy to Clipboard" width={15} height={15} title='Copy to Clipbaord' onClick={() => copyToClipboard(result)} role='button' />
                                    {result.savedStatus === true ? (
                                        <OverlayTrigger
                                            placement="bottom"
                                            overlay={
                                                <Tooltip id={`tooltip-bottom`}>
                                                    Already saved into the DB
                                                </Tooltip>
                                            }
                                        >
                                            <img src={save} alt="Save Prompt" width={15} height={15} role='button' />

                                        </OverlayTrigger>
                                    ) : (
                                        <img src={save} alt="Save Prompt" width={15} height={15} title='Save Prompt' onClick={() => handleShow(result)} role='button' />

                                    )}
                                    <img src={regenerate} alt="Regenerate Prompt" width={15} height={15} title='Regenerate Prompt' onClick={(e) => regeneratePrompt(e, result)} role='button' />
                                </div>

                            </div>
                        </div >
                    ))
                )
                    : (
                        <div className=' d-flex flex-column align-items-center'>
                            <img src={NoDataFound} alt="No Data Found" width={500} className='NoPromptFoundImage' />
                            {/* <p className='text-white h-100'>No Prompts Found</p> */}
                            <h1 className='text-white text-center'>Start creating your first prompt!</h1>
                        </div>
                    )

            )}

            <SaveModal
                selectedPrompt={selectedPrompt}
                handleShow={handleShow}
                show={showSaveDialog}
                setShowSaveDialog={setShowSaveDialog}
                setOpenAIResults={setOpenAIResults}
                id={selectedPrompt ? selectedPrompt.id : null}
            />
        </div>
    )
}

export default PromptResults