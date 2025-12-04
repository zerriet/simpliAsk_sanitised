import os
from smolagents.models import OpenAIServerModel

MODEL_ID = "gpt-4.1-mini"


def get_smol_model() -> OpenAIServerModel:
    """
    Create and return an OpenAIServerModel instance backed by the OPENAI_API_KEY.

    Returns:
        OpenAIServerModel: A model wrapper that smolagents can use to generate responses.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set in environment.")
    return OpenAIServerModel(
        model_id=MODEL_ID,
        api_key=api_key,
    )
