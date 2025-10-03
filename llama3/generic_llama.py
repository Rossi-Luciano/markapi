from config.settings.base import LLAMA_ENABLED, LLAMA_MODEL_DIR, MODEL_LLAMA

import os


class LlamaDisabledError(Exception):
    pass

class LlamaModelNotFoundError(FileNotFoundError):
    pass

class LlamaNotInstalledError(ImportError):
    pass

class GenericLlama:
  # Singleton pattern to cache the LLaMA model instance
  _cached_llm = None

  def __init__(self, messages, response_format, max_tokens=4000, temperature=0.5, top_p=0.5):
    self.messages = messages
    self.response_format = response_format
    self.max_tokens = max_tokens
    self.temperature = temperature
    self.top_p = top_p

    if not LLAMA_ENABLED:
      raise LlamaDisabledError("LLaMA is disabled in settings.")
    
  def run(self, user_input):
    input = self.messages.copy()
    input.append({
      'role': 'user',
      'content': user_input
    })
    return self.llm.create_chat_completion(messages=input, response_format=self.response_format, max_tokens=self.max_tokens, temperature=self.temperature, top_p=self.top_p)