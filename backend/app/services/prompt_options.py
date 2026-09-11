"""Ported from tru-prompt-frontend/src/components/openAIUtils.js so the AI
generation endpoint reproduces the exact same prompts server-side."""

OPTIONS_LIST = [
    {
        "name": "SEO",
        "param": "As an SEO expert, focus on tasks like on-page optimization (meta tags, content structure), off-page strategies (backlink building, outreach), and performing a comprehensive site audit to identify issues and opportunities",
    },
    {
        "name": "Design",
        "param": "As a designer, consider aspects such as user experience, visual aesthetics, brand consistency, and effective communication through design elements",
    },
    {
        "name": "Communication",
        "param": "As a communication specialist, focus on effective messaging, audience engagement, and strategies for clear and impactful communication across various channels",
    },
    {
        "name": "Web Development",
        "param": "As a web developer, consider aspects such as responsive design, performance optimization, accessibility, and modern web technologies",
    },
    {
        "name": "Lead Generation",
        "param": "As a lead generation expert, focus on strategies to attract and convert potential customers into qualified leads for the business",
    },
    {
        "name": "Lifecycle Marketing",
        "param": "As a lifecycle marketing specialist, focus on strategies for customer acquisition, retention, and growth across various stages of the customer journey",
    },
    {
        "name": "Business Development",
        "param": "As a business development professional, focus on strategies for growth, partnerships, market expansion, and improving overall business performance",
    },
]

_PARAM_BY_NAME = {option["name"]: option["param"] for option in OPTIONS_LIST}


def build_combined_options(selected_options: list[str]) -> str:
    # No default fallback -- selecting a function is optional on the frontend,
    # and picking none should mean "just work from the user's own prompt",
    # not silently apply an SEO-expert framing they never asked for.
    options = selected_options or []
    # A name outside the fixed list is a user-typed custom option (see "Other"
    # in HandlePrompt.jsx) -- use it as-is rather than dropping it, so it still
    # shapes the generated prompt instead of silently doing nothing.
    parts = [_PARAM_BY_NAME.get(name.strip(), name.strip()) for name in options]
    return " and ".join(part for part in parts if part)
