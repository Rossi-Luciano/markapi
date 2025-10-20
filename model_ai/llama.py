# Standard library imports
import logging
import os

from config.settings.base import (
    LLAMA_ENABLED,
    LLAMA_MODEL_DIR,
)

# Third-party imports
import google.generativeai as genai

# Local application imports
from model_ai import messages
from model_ai.exceptions import (
    LlamaDisabledError,
    LlamaModelNotFoundError,
    LlamaNotInstalledError,
)
from model_ai.models import LlamaModel


class LlamaService:
  # Singleton pattern to cache the LLaMA model instance
  _cached_llm = None

  def __init__(self, messages=None, response_format=None, max_tokens=4000, temperature=0.1, top_p=0.1, mode='chat', nthreads=2):
    self.messages = messages
    self.response_format = response_format
    self.max_tokens = max_tokens
    self.temperature = temperature
    self.top_p = top_p
    self.mode = mode

    if not LLAMA_ENABLED:
      raise LlamaDisabledError("LLaMA is disabled in settings.")
    
    if LlamaService._cached_llm is None:
      try:
         from llama_cpp import Llama
      except ImportError as e:
         raise LlamaNotInstalledError("The 'llama-cpp-python' package is not installed. Please use the llama-activated Docker image (Dockerfile.llama).") from e

      model_ai = LlamaModel.objects.first()
      if not model_ai:
        raise LlamaModelNotFoundError("No LLaMA model configured in the database. Please add a LLaMA model entry.")
    
      model_path = os.path.join(LLAMA_MODEL_DIR, model_ai.name_file)
      if not os.path.isfile(model_path):
        raise LlamaModelNotFoundError(f"LLaMA model file not found at {model_path}. Please ensure the model is downloaded and the path is correct.")

      try:
        LlamaService._cached_llm = Llama(model_path=model_path, n_ctx=max_tokens, n_threads=nthreads)
      except Exception as e:
        raise RuntimeError(f"Failed to initialize LLaMA model: {e}") from e
      
    self.llm = LlamaService._cached_llm

  def run(self, user_input):
    if self.mode == 'chat':
      return self._run_as_chat(user_input)
    elif self.mode == 'prompt':
      return self._run_as_content_generation(user_input)

  def _run_as_chat(self, user_input):
    """ Run LLaMA in chat mode."""
    input = self.messages.copy()
    input.append({
      'role': 'user',
      'content': user_input
    })
    return self.llm.create_chat_completion(
      messages=input, 
      response_format=self.response_format, 
      max_tokens=self.max_tokens, 
      temperature=self.temperature, 
      top_p=self.top_p
    )
  
  def _run_as_content_generation(self, user_input):
    """ Run LLaMA in completion mode."""
    model_ai = LlamaModel.objects.first()

    # Try to use Gemini if configured
    if model_ai and model_ai.api_key_gemini:

      # Setup Gemini API key
      genai.configure(api_key=model_ai.api_key_gemini)

      # Fetch the Gemini model
      # FIXME: Hardcoded model name
      model = genai.GenerativeModel('models/gemini-2.0-flash')

      # Generate content using Gemini
      return model.generate_content(user_input).text

    # Gemini not configured, fallback to LLaMA
    else:
      return self.llm(
        user_input, 
        max_tokens=self.max_tokens, 
        temperature=self.temperature, 
        stop=["\n\n"]
      )
  
class LlamaInputSettings:
    @staticmethod
    def get_first_metadata(text):
        logging.debug(messages.ALL_FIRST_BLOCK.format(text=text))
        return messages.ALL_FIRST_BLOCK.format(text=text)

    @staticmethod
    def get_doi_and_section():
        return messages.DOI_AND_SECTION_MESSAGES, messages.DOI_AND_SECTION_FORMAT

    @staticmethod
    def get_titles():
        return messages.TITLE_MESSAGES, messages.TITLE_RESPONSE_FORMAT

    @staticmethod
    def get_author_config():
        return messages.AUTHOR_MESSAGES, messages.AUTHOR_RESPONSE_FORMAT

    @staticmethod
    def get_affiliations():
        return messages.AFFILIATION_MESSAGES, messages.AFFILIATION_RESPONSE_FORMAT

    @staticmethod
    def get_reference():
        return messages.REFERENCE_MESSAGES, messages.REFERENCE_RESPONSE_FORMAT
  