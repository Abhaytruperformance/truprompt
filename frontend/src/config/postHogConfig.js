import posthog from 'posthog-js';

// Initialize PostHog
posthog.init('phc_lLmBXALfUQmoxsrdJA4LgWmdDKBHusUDlxZ8DH686R3', {
    api_host: 'https://us.i.posthog.com',
    persistence: 'cookie', // Use cookies for tracking users
    debug: true, // Enable debug mode
});

export default posthog;
