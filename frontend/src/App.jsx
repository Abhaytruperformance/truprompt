import React, { useState, useEffect } from "react";
import posthog from './config/postHogConfig';
import "bootstrap/dist/css/bootstrap.min.css";
import "./components/CSS/designSystem.css";
import { useMicrosoftLoginQuery } from "./store/slices/authSlice";
import Loading from './components/Loading'
import LoginScreen from "./components/LoginScreen";
import SideBar from "./components/SideBar";
import MainComponent from "./components/MainComponent";
import AcceptInvitePage from "./components/AcceptInvitePage";
import PublicSharePage from "./components/PublicSharePage";
import companyLogo from './assets/companyLogo.svg'


export default function TruPromptGenerator() {


  // Microsoft SSO
  const { data: userData, isLoading } = useMicrosoftLoginQuery();


  // const promptId = useSelector(selectPromptId);
  // console.log("Prompt Id: ", promptId);

  // const { data: singlePrompt, } = useGetSinglePromptQuery(promptId, {
  //   skip: !promptId,
  // });

  // const Results = useSelector(selectPromptSource);
  // console.log("Results", Results);


  const [selectedOptions, setSelectedOptions] = useState([]);
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  // const [mainComponent, setMainComponent] = useState('newChat');


  // to fetch the prompts stoed in the local storage 
  const [openAIResults, setOpenAIResults] = useState(() => {
    // Fetch data from local storage and parse it
    const storedData = localStorage.getItem('openAIResults');
    if (storedData) {
      const parsedData = JSON.parse(storedData);
      return parsedData.results || []; // Return results or an empty array if not found
    }
    return []; // Default to an empty array if no data is found
  });

  useEffect(() => {
    const cleanExpiredLocalStorage = () => {
      // Retrieve the data from localStorage
      const data = localStorage.getItem('openAIResults');
      if (data) {
        const parsedData = JSON.parse(data);

        // Filter out expired items
        const now = new Date().getTime();
        const updatedResults = parsedData.results.filter(item => {
          const expirationDate = new Date(item.expiration).getTime();
          return expirationDate > now; // Keep only non-expired items
        });

        if (updatedResults.length !== parsedData.results.length) {
          // If any items were removed, update localStorage
          localStorage.setItem(
            'openAIResults',
            JSON.stringify({ results: updatedResults })
          );
        }
      }
    };



    const postHogIntegration = () => {
      if (userData && userData.email) {
        // Identify the user in PostHog
        posthog.identify(userData.email, {
          name: userData.name,
          role: userData.role,
        });

        // Optionally, set additional properties for the user
        posthog.people.set({
          name: userData.name,
          email: userData.email,
          role: userData.role,
        });
      }
    }

    // Run the cleanup function when the component mounts
    cleanExpiredLocalStorage();

    postHogIntegration();
  }, [userData]); // Empty dependency array to run only once when App loads

  if (window.location.pathname === '/accept-invite') {
    return <AcceptInvitePage userData={userData} isLoading={isLoading} />;
  }

  if (window.location.pathname.startsWith('/share/')) {
    // Must render for logged-out visitors too -- true public access, no login gate.
    return <PublicSharePage />;
  }

  if (isLoading) { // Check for loading state
    return (
      <div className="container d-flex flex-column gap-3 mt-5 justify-content-center align-items-center">
        <Loading />
      </div>
    );
  }

  if (!userData) {
    return (
      <LoginScreen />
    );
  }

  return (
    <>
      {/* <Header userData={userData} /> */}


      {/* Offcanvas Sidebar */}
      <div className="offcanvas offcanvas-start" id="offcanvasSidebar" tabIndex="-1" aria-labelledby="offcanvasSidebarLabel">

        <div className="offcanvas-body p-0">
          <button type="button" className="btn-close btnOffcanvasClose" data-bs-dismiss="offcanvas" aria-label="Close"></button>
          <SideBar userData={userData} accordian={'Mobile'} />
        </div>
      </div>

      <div className="container-fluid " style={{ backgroundColor: '#151515' }}>
        <div className="row">
          {/* 
          <button
            className="btn btn-primary d-md-none"
            type="button"
            data-bs-toggle="offcanvas"
            data-bs-target="#offcanvasSidebar"
            aria-controls="offcanvasSidebar"
            sticky="top"
          >
            Open Sidebar
          </button> */}
          <div className="d-flex d-lg-none justify-content-between align-items-center sticky-top navDiv" >
            <a href="/"><img src={companyLogo} alt="Company Logo" width={200} height={30} /></a>
            <i
              className="fa-solid fa-bars fa-xl"
              style={{ color: '#FF5A24' }}
              type="button"
              data-bs-toggle="offcanvas"
              data-bs-target="#offcanvasSidebar"
              aria-controls="offcanvasSidebar"
            ></i>
          </div>
          <div className="col-12 col-lg-3 d-none d-lg-block p-0">
            <SideBar userData={userData} accordian={'Desktop'} />
          </div>
          <div className="col-12 col-lg-9 p-0">
            <MainComponent
              loading={loading}
              prompt={prompt}
              setPrompt={setPrompt}
              // mainComponent={mainComponent}
              userData={userData}
              setLoading={setLoading}
              selectedOptions={selectedOptions}
              openAIResults={openAIResults}
              setSelectedOptions={setSelectedOptions}
              setOpenAIResults={setOpenAIResults}
            />
          </div>
        </div>
      </div>

    </>
  );
}