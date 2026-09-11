import React from 'react'
import { OverlayTrigger, Popover } from 'react-bootstrap';
import Arrow from '../assets/accordionIcon.svg'
import AISubmit from '../assets/AISubmit.svg'

const UserInput = () => {

    const popover = (
        <Popover id="popover-basic" className="custom-popover">
            <Popover.Body>
                <button className="btn btn-danger"  >
                    Logout
                </button>
            </Popover.Body>
        </Popover>
    );

    return (
        <>
            <div className="d-flex flex-sm-row flex-column userInputDiv">
                <div className="selectFunctions" role='button'>
                    <OverlayTrigger
                        trigger="click"
                        placement='top'
                        overlay={popover}
                        rootClose
                    >
                        <div className="selectFunctionsDiv d-flex justify-content-between align-items-center">
                            <p className='selectFunctionsTitle'>Select Functions</p>
                            <img
                                src={Arrow}
                                width={18}
                                height={18}
                                alt='Arrow'
                                className='selectFunctionsArrow' />
                        </div>
                    </OverlayTrigger>
                </div>
                <div className="userInput d-flex">
                    <input
                        type="text"
                        placeholder='Message AI Prompt Generator'
                        className='userInputField'
                    />
                    <div className="AISubmit" role='button'>
                        <img
                            src={AISubmit}
                            width={24}
                            height={24}
                            alt='AI'
                            className=''
                        />

                    </div>

                </div>

            </div>
        </>
    )
}

export default UserInput