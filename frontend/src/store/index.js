// src/store/index.js
import { configureStore } from '@reduxjs/toolkit';
import { truPromptApi, promptReducer, promptResultsReducer } from './slices/truPromptSlice';
import { authApi } from './slices/authSlice';
import { orgApi } from './slices/orgSlice';

const store = configureStore({
    reducer: {
        prompt: promptReducer,
        promptResults: promptResultsReducer,
        [truPromptApi.reducerPath]: truPromptApi.reducer, //Add RTK Query reducer
        [authApi.reducerPath]: authApi.reducer, //Add Microsoft SSO login
        [orgApi.reducerPath]: orgApi.reducer, //Add org/team management
    },
    middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware().concat(truPromptApi.middleware, authApi.middleware, orgApi.middleware), // Add RTK Query middleware
});

export default store;
