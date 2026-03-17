from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI


def get_llm(provider, model, keys):

    if provider == "openai":
        return ChatOpenAI(
            model=model,
            api_key=keys["openai"]
        )

    if provider == "claude":
        return ChatAnthropic(
            model=model,
            api_key=keys["claude"]
        )

    if provider == "gemini":
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=keys["gemini"]
        )

    raise ValueError("Unknown provider")