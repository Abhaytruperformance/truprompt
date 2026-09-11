import React from "react";
import "bootstrap/dist/css/bootstrap.min.css";
import { useLogoutMutation } from "./store/slices/authSlice";
import Swal from "sweetalert2";
// import 'font-awesome/css/font-awesome.min.css';

export default function Header({ userData }) {



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

  return (
    <header className="container border-bottom header-bar">
      <div className="row align-items-center">
        <div className="col-6 d-flex align-items-center">
          {/* Add your logo image here */}
          <img
            src="/images/logo.png"
            alt="Logo"
            className="img-fluid header-logo"
            style={{ maxHeight: "50px" }}
          />
        </div>
        <div className="col-6 text-end d-flex gap-3 justify-content-end align-items-center">
          {/* {console.log(userData)} */}
          {userData.profileImage !== '404' ? (
            <img src={userData.profileImage} alt="Profile" width={48} className="rounded-circle" />
          ) : (
            <i className="fa fa-user-circle fa-2x" aria-hidden="true"></i>

          )}
          <div className="d-flex flex-column align-items-start">
            <span>{userData.name}</span>
            <span>{userData.email}</span>
          </div>
          <button className="btn btn-primary" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
