import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import { createSlice } from '@reduxjs/toolkit';
import Cookies from 'js-cookie';


const token = Cookies.get('token');


const createRequest = (url) => ({
    url,
    headers: {
        'Authorization': `Bearer ${token}` // Ensure the token is valid
    }
});

const buildQuery = (filters = {}) => {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
        if (value) params.set(key, value);
    });
    const qs = params.toString();
    return qs ? `?${qs}` : '';
};


export const truPromptApi = createApi({
    reducerPath: 'truPromptApi',
    baseQuery: fetchBaseQuery({
        baseUrl: `${process.env.REACT_APP_BACKEND_URL}/api`,
        credentials: 'include',
    }),
    tagTypes: ['Prompts'],
    endpoints: (builder) => ({
        // Fetch all Prompts
        GetPrompts: builder.query({
            query: (filters) => ({
                method: 'GET',
                ...createRequest(`/prompts/${buildQuery(filters)}`),
            }),
            transformResponse: (response) => response.allPrompts,
            providesTags: ['Prompts'],
        }),
        getAuthPrompts: builder.query({
            query: (filters) => ({
                method: 'GET',
                ...createRequest(`/prompts/auth/verifiedUserPrompts/${buildQuery(filters)}`),
            }),
            transformResponse: (response) => response.allPrompts,
            providesTags: ['Prompts'],
        }),
        // Fetch Single Prompt
        getSinglePrompt: builder.query({
            // query: (id) => `/prompts/${id}`,
            query: (id) => ({
                method: 'GET',
                ...createRequest(`/prompts/${id}`),
            }),
            transformResponse: (response) => response.prompt,
            providesTags: (result, error, id) => [{ type: 'Prompts', id }]
        }),
        // Post a new Prompt
        postPrompt: builder.mutation({
            query: (newPrompt) => ({
                method: 'POST',
                body: newPrompt,
                ...createRequest(`/prompts/auth/verifiedUserPrompts/`),
            }),
            transformResponse: (response) => response,
            invalidatesTags: ['Prompts'],
        }),
        updatePromptCount: builder.mutation({
            query: (id) => ({
                method: 'PATCH',
                ...createRequest(`/prompts/updatePromptCount/${id}`),
            }),
            invalidatesTags: (result, error, { id }) => [{ type: 'Prompts', id }],
        }),
        updatePrompt: builder.mutation({
            query: ({ id, ...updatedPrompt }) => ({
                url: `/prompts/${id}`,
                method: 'PATCH',
                body: updatedPrompt,
            }),
            invalidatesTags: (result, error, { id }) => [{ type: 'Prompts', id }],
        }),
        deletePrompt: builder.mutation({
            query: (id) => ({
                method: 'DELETE',
                ...createRequest(`/prompts/${id}`),
            }),
            invalidatesTags: ['Prompts'],
        }),
        updatePromptCustomFields: builder.mutation({
            query: ({ id, values }) => ({
                url: `/prompts/${id}/custom-fields`,
                method: 'PUT',
                body: { values },
            }),
            invalidatesTags: (result, error, { id }) => [{ type: 'Prompts', id }],
        }),
        updatePromptTags: builder.mutation({
            query: ({ id, tagIds }) => ({
                url: `/prompts/${id}/tags`,
                method: 'PUT',
                body: { tagIds },
            }),
            invalidatesTags: (result, error, { id }) => [{ type: 'Prompts', id }],
        }),
        getPromptVersions: builder.query({
            query: (id) => ({
                method: 'GET',
                ...createRequest(`/prompts/${id}/versions`),
            }),
            transformResponse: (response) => response.versions,
            providesTags: (result, error, id) => [{ type: 'Prompts', id }],
        }),
        restorePromptVersion: builder.mutation({
            query: ({ id, versionId }) => ({
                url: `/prompts/${id}/versions/${versionId}/restore`,
                method: 'POST',
            }),
            invalidatesTags: (result, error, { id }) => [{ type: 'Prompts', id }],
        }),
        createShare: builder.mutation({
            query: ({ id, password, generationLimit }) => ({
                url: `/prompts/${id}/share`,
                method: 'POST',
                body: { password: password || undefined, generationLimit: generationLimit || undefined },
            }),
            invalidatesTags: (result, error, { id }) => [{ type: 'Prompts', id }],
        }),
        getShares: builder.query({
            query: (id) => ({
                method: 'GET',
                ...createRequest(`/prompts/${id}/share`),
            }),
            transformResponse: (response) => response.shares,
            providesTags: (result, error, id) => [{ type: 'Prompts', id }],
        }),
        revokeShare: builder.mutation({
            query: ({ id, shareId }) => ({
                url: `/prompts/${id}/share/${shareId}`,
                method: 'DELETE',
            }),
            invalidatesTags: (result, error, { id }) => [{ type: 'Prompts', id }],
        }),
        updatePromptStatus: builder.mutation({
            query: ({ id, status }) => ({
                url: `/prompts/${id}/status`,
                method: 'PATCH',
                body: { status },
            }),
            invalidatesTags: ['Prompts'],
        }),
        updatePromptRating: builder.mutation({
            query: ({ id, rating }) => ({
                url: `/prompts/${id}/rating`,
                method: 'PUT',
                body: { rating },
            }),
            invalidatesTags: (result, error, { id }) => [{ type: 'Prompts', id }, 'Prompts'],
        }),
    }),
});

const promptSlice = createSlice({
    name: 'prompt',
    initialState: {
        promptId: null,
        selectedOptions: [],
        // prompt: "",
        loading: false,
        currentPrompt: "",
        mainComponent: 'newChat',
        isDropdownOpen: false,
    },
    reducers: {
        setPromptId: (state, action) => {
            state.promptId = action.payload;
        },
        setSelectedOptions: (state, action) => {
            state.selectedOptions = action.payload;
        },
        // setPrompt: (state, action) => {
        //     state.prompt = action.payload;
        // },
        setLoading: (state, action) => {
            state.loading = action.payload;
        },
        setCurrentPrompt: (state, action) => {
            state.currentPrompt = action.payload;
        },
        setMainComponent: (state, action) => {
            state.mainComponent = action.payload;
        },
        setIsDropdownOpen: (state, action) => { // Add this reducer
            state.isDropdownOpen = action.payload;
        },
    },
});

// Selectors
export const selectPromptId = (state) => state.prompt.promptId;
export const SelectedOptions = (state) => state.prompt.selectedOptions;
// export const Prompt = (state) => state.prompt.prompt;
export const Loading = (state) => state.prompt.loading;
export const CurrentPrompt = (state) => state.prompt.currentPrompt;
export const selectMainComponent = (state) => state.prompt.mainComponent;
export const selectIsDropdownOpen = (state) => state.prompt.isDropdownOpen;


// Export actions
export const {
    setPromptId,
    setSelectedOptions,
    // setPrompt, 
    setLoading,
    setCurrentPrompt,
    setMainComponent,
    setIsDropdownOpen } = promptSlice.actions;
export const promptReducer = promptSlice.reducer;



const promptResultsSlice = createSlice({
    name: 'promptResults',
    initialState: {
        // promptSource: 'openAIPrompts', // To list all saved prompts in the local storage
        promptSource: 'singlePrompt', // Default source
        openAIResults: [],
    },
    reducers: {
        setPromptSource(state, action) {
            state.promptSource = action.payload; // Set the source to either 'openAI' or 'single'
        },
        clearResults(state) {
            state.promptSource = ''; // Reset to default
        },
        setOpenAIResults(state, action) { // Add this reducer
            state.openAIResults = action.payload; // Update openAIResults
        },
    },
});

export const { setPromptSource, clearResults, setOpenAIResults } = promptResultsSlice.actions;

export const selectPromptSource = (state) => state.promptResults.promptSource;
export const OpenAIResults = (state) => state.promptResults.openAIResults;
export const promptResultsReducer = promptResultsSlice.reducer;


export const {
    useGetAuthPromptsQuery,
    useGetPromptsQuery,
    useGetSinglePromptQuery,
    usePostPromptMutation,
    useUpdatePromptMutation,
    useUpdatePromptCountMutation,
    useDeletePromptMutation,
    useUpdatePromptCustomFieldsMutation,
    useUpdatePromptTagsMutation,
    useGetPromptVersionsQuery,
    useLazyGetPromptVersionsQuery,
    useRestorePromptVersionMutation,
    useCreateShareMutation,
    useGetSharesQuery,
    useRevokeShareMutation,
    useUpdatePromptStatusMutation,
    useUpdatePromptRatingMutation,
} = truPromptApi;