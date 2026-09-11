// openAIUtils.js
import Swal from 'sweetalert2';
import '@sweetalert2/theme-dark';
import { setPromptSource } from '../store/slices/truPromptSlice';

// Function to update OpenAI results and store them in local storage
export const updateOpenAIResults = (setOpenAIResults, newResults) => {
    setOpenAIResults(prevResults => {
        const currentResults = Array.isArray(prevResults) ? prevResults : [];

        const updatedResults = [
            ...currentResults,
            ...newResults.map(result => ({
                ...result,
                savedStatus: false,
                promptDBId: "",
                // expiration: new Date(Date.now() + 5 * 1000).toISOString() // Set expiration for 5 seconds (example)
                expiration: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString() // Set expiration for 30 days
            }))
        ];

        // Store in local storage
        const dataToStore = {
            results: updatedResults
        };
        localStorage.setItem('openAIResults', JSON.stringify(dataToStore));

        return updatedResults; // Return updated results for state
    });
};

// Raw generation call, shared by the single-generate flow (handlePromptSearch
// below) and the Playground's parallel multi-model comparison. `model` is
// optional -- omitting it keeps the server's existing default-model behavior.
// `allowFallback` defaults true (New Chat's existing behavior); Playground
// passes false so a card labeled for a specific model never silently shows
// a different model's output.
export const generateWithModel = async (prompt, selectedOptions, model = null, extraContext = null, allowFallback = true) => {
    // Prompt generation runs server-side so the OpenAI/OpenRouter key never reaches the browser
    const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/ai/generate-prompt`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userPrompt: prompt, selectedOptions, model, extraContext, allowFallback }),
    });

    if (!res.ok) {
        const error = new Error(`Error ${res.status}`);
        error.code = res.status;
        throw error;
    }

    return res.json();
};

// Extracts text from an uploaded file to use as extra generation context.
export const extractFromFile = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/ai/extract-file`, {
        method: 'POST',
        credentials: 'include',
        body: formData,
    });
    if (!res.ok) {
        const error = new Error(`Error ${res.status}`);
        error.code = res.status;
        throw error;
    }
    return res.json();
};

// Extracts visible text from a URL to use as extra generation context.
export const extractFromUrl = async (url) => {
    const res = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/ai/extract-url`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
    });
    if (!res.ok) {
        const error = new Error(`Error ${res.status}`);
        error.code = res.status;
        throw error;
    }
    return res.json();
};

// Function to handle prompt search
export const handlePromptSearch = async (
    e,
    prompt,
    setPrompt,
    setLoading,
    setOpenAIResults,
    selectedOptions,
    setSelectedOptions,
    dispatch,
    model = null,
    extraContext = null,
    contextSource = null // { sourceType, sourceName } -- carried onto the result so SaveModal can persist it alongside the prompt
) => {

    e.preventDefault();

    if (prompt) {
        setLoading(true);

        const handleError = (error) => {
            let errorMessage = 'An unexpected error occurred. Please try again later.';
            const errorCode = error.response?.status || error.code || null;
            // console.log('err:', error);


            if (errorCode === 429) {
                errorMessage = 'You have exceeded your current quota. Please check your plan and billing details.';
            } else if (errorCode === 401) {
                errorMessage = 'Unauthorized access. Please verify your API key or login credentials.';
            } else if (errorCode === 500) {
                errorMessage = 'A server error occurred. Please try again later.';
            } else if (errorCode === 400) {
                errorMessage = 'Bad request. Please check your input and try again.';
            }

            Swal.fire({
                title: 'Error!',
                text: errorMessage,
                icon: 'error',
                confirmButtonText: 'OK',
                theme: 'dark'
            });
        };

        try {
            const structuredResponse = await generateWithModel(prompt, selectedOptions, model, extraContext);

            if (extraContext && contextSource) {
                structuredResponse.sourceType = contextSource.sourceType;
                structuredResponse.sourceName = contextSource.sourceName;
                structuredResponse.sourceContext = extraContext;
            }

            // Update the OpenAI results using the utility function
            updateOpenAIResults(setOpenAIResults, [structuredResponse]);

            // Reset selectedOptions and prompt to empty
            setSelectedOptions([]);
            setPrompt("");

            // Dispatch an action (if applicable)
            dispatch(setPromptSource('openAIPrompts'));
            // dispatch(setPromptSource('singlePrompt'));
        } catch (error) {
            console.error('Error fetching from OpenAI API:', error);
            handleError(error)
        } finally {
            setLoading(false);
        }
    } else {
        Swal.fire({
            title: 'Error!',
            text: 'Please provide the prompt...',
            icon: 'error',
            confirmButtonText: 'OK',
            theme: 'dark'
        });
    }
};
