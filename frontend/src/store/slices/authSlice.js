import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import Cookies from 'js-cookie';

const token = Cookies.get('token');


const createRequest = (url) => ({
    url,
    headers: {
        'Authorization': `Bearer ${token}` // Ensure the token is valid
    }
});


export const authApi = createApi({
    reducerPath: 'authApi',
    baseQuery: fetchBaseQuery({
        baseUrl: `${process.env.REACT_APP_BACKEND_URL}/api`,
        credentials: 'include',
    }),
    endpoints: (builder) => ({
        // Endpoint to log in with Microsoft SSO
        microsoftLogin: builder.query({
            query: () => ({
                method: 'GET',
                ...createRequest(`/users/auth/microsoft`),
            }),
            transformResponse: (response) => {
                // Assuming the response has the user data you want to store
                return response.user || null; // return user or null if not available
            },
        }),
        // Endpoint to log out the user
        logout: builder.mutation({
            query: () => ({
                method: 'GET',
                url: '/users/auth/logout',
            })
        }),
        allUsers: builder.query({
            query: () => ({
                method: 'GET',
                ...createRequest(`/users/allusers`),
            }),
            transformResponse: (response) => response.allUsers
        })
    })
});


export const { useMicrosoftLoginQuery, useLogoutMutation, useAllUsersQuery } = authApi;