"""Language models for the apps.

The user enters each provider's API key once, in Settings (`llm` in config.json),
and every app picks a provider from those. All of them speak the OpenAI chat
completions format, so one HTTP call covers them and apps need no SDK:

    import theticketpost.llm as llm
    text = llm.chat(provider, [{"role": "user", "content": "Hi"}], model=None)
"""

import json
import os

import requests
from loguru import logger

import theticketpost.settings

# id -> name shown in the UI, endpoint, model used when the app leaves it empty
PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-5.6-terra",
        "keys_url": "https://platform.openai.com/api-keys",
    },
    "anthropic": {
        "name": "Anthropic (Claude)",
        "base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-sonnet-5-5",
        "keys_url": "https://console.anthropic.com/settings/keys",
        # its OpenAI compatible endpoint doesn't take response_format
        "json_mode": False,
    },
    "gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-flash-latest",
        "keys_url": "https://aistudio.google.com/apikey",
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
        "keys_url": "https://platform.deepseek.com/api_keys",
    },
    "mistral": {
        "name": "Mistral",
        "base_url": "https://api.mistral.ai/v1",
        "default_model": "mistral-small-latest",
        "keys_url": "https://console.mistral.ai/api-keys",
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "openrouter/auto",
        "keys_url": "https://openrouter.ai/settings/keys",
    },
    "ollama": {
        "name": "Ollama (local)",
        # docker-compose.yml sets OLLAMA_URL to its ollama container
        "base_url": os.environ.get("OLLAMA_URL", "http://localhost:11434/v1"),
        "default_model": "llama3.2",
        # runs on your machine: no key, the address can change
        "needs_key": False,
    },
}

TIMEOUT = 120


class LLMError(Exception):
    """A message that can be shown on the ticket or in the log (never contains the key)."""


def settings():
    return theticketpost.settings.get_json("config").get("llm", {})


def provider_settings(provider_id):
    return settings().get(provider_id, {})


def is_configured(provider_id):
    provider = PROVIDERS.get(provider_id)
    if not provider:
        return False
    if provider.get("needs_key", True):
        return bool(provider_settings(provider_id).get("api_key"))
    return bool(provider_settings(provider_id).get("enabled"))


def providers():
    """Every provider, for the UI. Keys are not included."""
    return [
        {
            "id": provider_id,
            "name": provider["name"],
            "default_model": provider["default_model"],
            "default_base_url": provider["base_url"],
            "needs_key": provider.get("needs_key", True),
            "keys_url": provider.get("keys_url"),
            "configured": is_configured(provider_id),
        }
        for provider_id, provider in PROVIDERS.items()
    ]


def chat(provider_id, messages, model=None, json_output=False):
    """Send a chat to the provider and return the answer's text.

    json_output asks for a JSON object where the provider supports it; the
    prompt should ask for JSON too. Raises LLMError."""
    provider = PROVIDERS.get(provider_id)
    if not provider:
        raise LLMError(f"Unknown AI provider '{provider_id}'")
    if not is_configured(provider_id):
        raise LLMError(f"{provider['name']} is not set up: add it in Settings > AI providers")

    config = provider_settings(provider_id)
    base_url = (config.get("base_url") or provider["base_url"]).rstrip("/")
    body = {"model": model or provider["default_model"], "messages": messages}
    if json_output and provider.get("json_mode", True):
        body["response_format"] = {"type": "json_object"}
    headers = {"Content-Type": "application/json"}
    if config.get("api_key"):
        headers["Authorization"] = "Bearer " + config["api_key"]

    try:
        response = requests.post(base_url + "/chat/completions", json=body, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise LLMError(f"Could not reach {provider['name']}: {type(e).__name__}") from e

    if response.status_code != 200:
        message = error_message(response)
        if provider_id == "ollama" and response.status_code == 404:
            message += f". Download it with: ollama pull {body['model']}"
        raise LLMError(f"{provider['name']} error {response.status_code}: {message}")

    try:
        text = response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise LLMError(f"Unexpected answer from {provider['name']}") from e
    return strip_code_fence(text) if json_output else text


def chat_json(provider_id, messages, model=None):
    """chat() for a JSON object answer, parsed."""
    text = chat(provider_id, messages, model=model, json_output=True)
    try:
        return json.loads(text)
    except ValueError as e:
        raise LLMError("The AI answer is not valid JSON") from e


def error_message(response):
    try:
        error = response.json().get("error", {})
        message = error.get("message") if isinstance(error, dict) else str(error)
    except ValueError:
        message = None
    return (message or response.reason or "")[:200]


def strip_code_fence(text):
    """Some models wrap JSON in ```json ... ``` even when asked not to."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def migrate_app_keys():
    """Apps used to keep their own OpenAI key. Move the first one found to
    Settings so those apps keep working after updating."""
    config = theticketpost.settings.get_json("config")
    if not config or config.get("llm", {}).get("openai", {}).get("api_key"):
        return
    apps_folder = os.path.join(theticketpost.settings.get_storage_path(), "apps")
    if not os.path.isdir(apps_folder):
        return
    for app_name in sorted(os.listdir(apps_folder)):
        path = os.path.join(apps_folder, app_name, "config.json")
        try:
            with open(path) as config_file:
                items = json.load(config_file)
        except (OSError, ValueError):
            continue
        for item in items if isinstance(items, list) else []:
            if "openai" in str(item.get("label", "")).lower() and "key" in str(item.get("name", "")).lower() and item.get("value"):
                config.setdefault("llm", {}).setdefault("openai", {})["api_key"] = item["value"]
                theticketpost.settings.save_json("config", config)
                logger.info(f"Moved the OpenAI key of {app_name} to Settings > AI providers")
                return
