import React from 'react'
import companyLogo from '../assets/companyLogo.svg'
import microsftSSO from '../assets/microsoftSSO.svg'
import './CSS/LoginScreen.css'

const LoginScreen = () => {
    const orgSlug = new URLSearchParams(window.location.search).get('org');

    return (
        <div className="container-fluid LoginScreen">
            <div className="row justify-content-center">
                <div className="col-12 col-md-7 d-flex justify-content-center align-items-center divLoginContainer">
                    <div className="loginContainer text-center">
                        <img src={companyLogo} alt="Company Logo" className='companyLogo' />
                        <p className='singIn'>Sign in</p>
                        <img src={microsftSSO} alt="microsoft SSO" className='cursor-pointer microsoftSSO' role="button" onClick={() => window.location.href = `${process.env.REACT_APP_BACKEND_URL}/api/users/auth/microsoft`} />
                        {orgSlug && (
                            <button
                                type="button"
                                className="btn-primary mt-3"
                                onClick={() => window.location.href = `${process.env.REACT_APP_BACKEND_URL}/api/orgs/auth/workos?org=${encodeURIComponent(orgSlug)}`}
                            >
                                Continue with company SSO
                            </button>
                        )}
                    </div>
                </div>
                {/* Quiet supporting element, not the page's focus -- hidden below
                    768px so a small screen is 100% "log in," no demo to scroll past. */}
                <div className="col-md-5 d-none d-md-flex align-items-center justify-content-center loginDemoCol">
                    <div className="loginDemo">
                        <p className="loginDemoRough">"make seo report"</p>
                        <div className="loginDemoArrow">↓</div>
                        <p className="loginDemoRefined">
                            "Analyze the attached SEO performance data and identify the top three opportunities for organic growth, ranked by estimated impact..."
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default LoginScreen
