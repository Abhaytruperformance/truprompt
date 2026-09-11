import React from 'react'
import './CSS/SideBar.css'
import companyLogo from '../assets/companyLogo.svg'
import GetPrompts from './GetPrompts'
import UserProfile from './UserProfile'
import NewChatTab from './NewChatTab'
import History from './History'
import TeamTab from './TeamTab'
import ManageTab from './ManageTab'
import PlaygroundTab from './PlaygroundTab'
import AnalyticsTab from './AnalyticsTab'

const SideBar = ({ userData, accordian }) => {
    return (
        <div className='sideBarDiv d-flex flex-column align-items-center justify-content-between'>
            <div className='d-flex flex-column align-items-center justify-content-between w-100'>
                <img src={companyLogo} alt="Company Logo" width={200} height={30} style={{ marginBottom: "var(--space-8)" }} />

                <div className="navGroup w-100">
                    <p className="navGroupLabel">Workspace</p>
                    <NewChatTab />
                    <div className="accordion w-100" id={`promptsAccordian${accordian}`}>
                        <GetPrompts auth={false} accordian={accordian} />
                        <GetPrompts auth={true} accordian={accordian} />
                    </div>
                    <History />
                    <PlaygroundTab />
                </div>

                <div className="navGroup w-100">
                    <p className="navGroupLabel">Organization</p>
                    <AnalyticsTab />
                    <TeamTab />
                    <ManageTab />
                </div>
            </div>
            <div className='w-100'>
                <hr />
                <UserProfile userData={userData} />

            </div>

        </div>
    )
}

export default SideBar