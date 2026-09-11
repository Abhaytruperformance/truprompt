import React, { useState, useEffect } from 'react'
import RightArrow from '../assets/RightArrow.svg'
import { OverlayTrigger, Popover } from 'react-bootstrap';
import Swal from "sweetalert2";
import { useLogoutMutation } from "../store/slices/authSlice";



const UserProfile = ({ userData }) => {

    const [placement, setPlacement] = useState('right');

    // Function to determine placement based on window width
    const determinePlacement = () => {
        if (window.innerWidth < 768) { // Bootstrap's breakpoint for mobile
            setPlacement('top');
        } else {
            setPlacement('right');
        }
    };

    useEffect(() => {
        determinePlacement(); // Set initial placement
        window.addEventListener('resize', determinePlacement); // Update on resize

        return () => {
            window.removeEventListener('resize', determinePlacement); // Cleanup
        };
    }, []);


    const [logout] = useLogoutMutation(); // Use the mutation hook

    const handleLogout = async () => {
        try {
            await logout().unwrap(); // Call the logout function
            // console.log("Logout Status: :", response);
            window.location.reload();
            // Optionally, you can dispatch an action to clear user data from Redux here
        } catch (error) {
            Swal.fire({ // Show error alert
                title: 'Logout Error!',
                text: 'Unable to logout. Please try after some time...',
                icon: 'error',
                confirmButtonText: 'OK',
                theme: 'dark'
            });
        }
    };
    // Define the popover with a logout button
    const popover = (
        <Popover id="popover-basic" className="custom-popover">
            <Popover.Body>
                <button className="btn btn-danger" onClick={handleLogout} >
                    Logout
                </button>
            </Popover.Body>
        </Popover>
    );
    return (
        <>
            <OverlayTrigger
                trigger="click"
                placement={placement}
                overlay={popover}
                rootClose
            >
                <div className='userProfile d-flex justify-content-between w-100' role='button'>

                    {/* <img src={newChatIcon} alt="New Chat" width={24} height={24} /> */}
                    <div className="text-end d-flex gap-2 justify-content-end align-items-center">
                        {/* {console.log(userData)} */}
                        {userData.profileImage !== '404' ? (
                            <img src={userData.profileImage} alt="Profile" width={38} className="rounded-circle" />
                        ) : (
                            <i className="fa fa-user-circle fa-2x" aria-hidden="true" style={{ color: '#FF5A24' }}></i>

                        )}
                        <div className="d-flex flex-column align-items-start">
                            <span className='profileName text-white'>{userData.name}</span>
                            <span className='profileEmail'>{userData.email}</span>
                        </div>
                    </div>
                    <img
                        src={RightArrow}
                        alt="Profile"
                        width={18}
                        className="rounded-circle"

                    />

                    {/* <button className="btn btn-primary" onClick={handleLogout}>
                        Logout
                        </button> */}
                </div>
            </OverlayTrigger>
        </>
    )
}

export default UserProfile