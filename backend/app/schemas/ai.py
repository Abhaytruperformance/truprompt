from pydantic import BaseModel


class GeneratePromptRequest(BaseModel):
    userPrompt: str
    selectedOptions: list[str] = []
    model: str | None = None
    extraContext: str | None = None
    # Playground (comparing named models against each other) sets this False --
    # a card labeled for a specific model must either show that model's real
    # output or a clear failure, never a silently substituted model. New
    # Chat's regular generation keeps the default True (unchanged behavior).
    allowFallback: bool = True


class ExtractUrlRequest(BaseModel):
    url: str
