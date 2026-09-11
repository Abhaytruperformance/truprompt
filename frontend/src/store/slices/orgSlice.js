import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import Cookies from 'js-cookie';

const token = Cookies.get('token');

const createRequest = (url) => ({
    url,
    headers: {
        'Authorization': `Bearer ${token}`
    }
});

export const orgApi = createApi({
    reducerPath: 'orgApi',
    baseQuery: fetchBaseQuery({
        baseUrl: `${process.env.REACT_APP_BACKEND_URL}/api`,
        credentials: 'include',
    }),
    tagTypes: ['Org'],
    endpoints: (builder) => ({
        getMyOrg: builder.query({
            query: () => ({
                method: 'GET',
                ...createRequest(`/orgs/me`),
            }),
            providesTags: ['Org'],
        }),
        getMembers: builder.query({
            query: () => ({
                method: 'GET',
                ...createRequest(`/orgs/members`),
            }),
            transformResponse: (response) => response.members,
            providesTags: ['Org'],
        }),
        updateMemberRole: builder.mutation({
            query: ({ userId, role }) => ({
                method: 'PATCH',
                body: { role },
                ...createRequest(`/orgs/members/${userId}`),
            }),
            invalidatesTags: ['Org'],
        }),
        updateWorkosConnection: builder.mutation({
            query: (connectionId) => ({
                method: 'PUT',
                body: { connectionId: connectionId || null },
                ...createRequest(`/orgs/me/workos-connection`),
            }),
            invalidatesTags: ['Org'],
        }),
        getInvitations: builder.query({
            query: () => ({
                method: 'GET',
                ...createRequest(`/orgs/invitations`),
            }),
            transformResponse: (response) => response.invitations,
            providesTags: ['Org'],
        }),
        inviteMember: builder.mutation({
            query: ({ email, role }) => ({
                method: 'POST',
                body: { email, role },
                ...createRequest(`/orgs/invitations`),
            }),
            invalidatesTags: ['Org'],
        }),
        acceptInvite: builder.mutation({
            query: (token) => ({
                method: 'POST',
                body: { token },
                ...createRequest(`/orgs/invitations/accept`),
            }),
            invalidatesTags: ['Org'],
        }),
        cancelInvitation: builder.mutation({
            query: (id) => ({
                method: 'DELETE',
                ...createRequest(`/orgs/invitations/${id}`),
            }),
            invalidatesTags: ['Org'],
        }),
        getDepartments: builder.query({
            query: () => ({
                method: 'GET',
                ...createRequest(`/departments/`),
            }),
            transformResponse: (response) => response.departments,
            providesTags: ['Org'],
        }),
        createDepartment: builder.mutation({
            query: (name) => ({
                method: 'POST',
                body: { name },
                ...createRequest(`/departments/`),
            }),
            invalidatesTags: ['Org'],
        }),
        deleteDepartment: builder.mutation({
            query: (id) => ({
                method: 'DELETE',
                ...createRequest(`/departments/${id}`),
            }),
            invalidatesTags: ['Org'],
        }),
        getCustomFields: builder.query({
            query: () => ({
                method: 'GET',
                ...createRequest(`/custom-fields/`),
            }),
            transformResponse: (response) => response.customFields,
            providesTags: ['Org'],
        }),
        createCustomField: builder.mutation({
            query: ({ name, fieldType, options }) => ({
                method: 'POST',
                body: { name, fieldType, options },
                ...createRequest(`/custom-fields/`),
            }),
            invalidatesTags: ['Org'],
        }),
        deleteCustomField: builder.mutation({
            query: (id) => ({
                method: 'DELETE',
                ...createRequest(`/custom-fields/${id}`),
            }),
            invalidatesTags: ['Org'],
        }),
        getTags: builder.query({
            query: () => ({
                method: 'GET',
                ...createRequest(`/tags/`),
            }),
            transformResponse: (response) => response.tags,
            providesTags: ['Org'],
        }),
        createTag: builder.mutation({
            query: (name) => ({
                method: 'POST',
                body: { name },
                ...createRequest(`/tags/`),
            }),
            invalidatesTags: ['Org'],
        }),
        deleteTag: builder.mutation({
            query: (id) => ({
                method: 'DELETE',
                ...createRequest(`/tags/${id}`),
            }),
            invalidatesTags: ['Org'],
        }),
        getApiKeys: builder.query({
            query: () => ({
                method: 'GET',
                ...createRequest(`/api-keys/`),
            }),
            transformResponse: (response) => response.apiKeys,
            providesTags: ['Org'],
        }),
        createApiKey: builder.mutation({
            query: ({ name, scopes }) => ({
                method: 'POST',
                body: { name, scopes },
                ...createRequest(`/api-keys/`),
            }),
            invalidatesTags: ['Org'],
        }),
        revokeApiKey: builder.mutation({
            query: (id) => ({
                method: 'DELETE',
                ...createRequest(`/api-keys/${id}`),
            }),
            invalidatesTags: ['Org'],
        }),
        getModels: builder.query({
            query: () => ({
                method: 'GET',
                ...createRequest(`/ai/models`),
            }),
            transformResponse: (response) => response.models,
        }),
        getAnalytics: builder.query({
            query: () => ({
                method: 'GET',
                ...createRequest(`/orgs/analytics`),
            }),
            providesTags: ['Org'],
        }),
    }),
});

export const {
    useGetMyOrgQuery,
    useGetMembersQuery,
    useUpdateMemberRoleMutation,
    useGetInvitationsQuery,
    useInviteMemberMutation,
    useAcceptInviteMutation,
    useCancelInvitationMutation,
    useGetDepartmentsQuery,
    useCreateDepartmentMutation,
    useDeleteDepartmentMutation,
    useGetCustomFieldsQuery,
    useCreateCustomFieldMutation,
    useDeleteCustomFieldMutation,
    useGetTagsQuery,
    useCreateTagMutation,
    useDeleteTagMutation,
    useGetApiKeysQuery,
    useCreateApiKeyMutation,
    useRevokeApiKeyMutation,
    useGetModelsQuery,
    useGetAnalyticsQuery,
    useUpdateWorkosConnectionMutation,
} = orgApi;
