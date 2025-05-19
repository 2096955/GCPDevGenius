import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple
import base64
from pathlib import Path

import google.generativeai as genai

logger = logging.getLogger(__name__)

class GeminiAIProvider:
    """Provider for Gemini API integration."""
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 model_name: str = "gemini-1.5-pro",
                 max_tokens: int = 4096,
                 temperature: float = 0.2,
                 top_p: float = 0.9,
                 top_k: int = 40,
                 safety_settings: Optional[Dict[str, str]] = None):
        """Initialize Gemini API provider.
        
        Args:
            api_key: Google API key for Gemini (default: from environment variable)
            model_name: Gemini model name
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature for sampling (0.0 to 1.0)
            top_p: Top-p sampling parameter (0.0 to 1.0)
            top_k: Top-k sampling parameter
            safety_settings: Safety settings for model generation
        """
        # Get API key from environment variable if not provided
        if api_key is None:
            api_key = os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                logger.warning("No API key provided for Gemini. Either pass api_key or set GOOGLE_API_KEY environment variable.")
        
        self.api_key = api_key
        self.model_name = model_name
        self.generation_config = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k
        }
        self.safety_settings = safety_settings
        
        # Initialize Gemini API
        if self.api_key:
            genai.configure(api_key=self.api_key)
        
    def _get_model(self):
        """Get the Gemini model."""
        return genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings
        )
    
    async def generate_text(self, prompt: str) -> str:
        """Generate text asynchronously.
        
        Args:
            prompt: Text prompt
        
        Returns:
            Generated text
        """
        # Execute in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._generate_text_sync, prompt)
    
    def _generate_text_sync(self, prompt: str) -> str:
        """Generate text synchronously (for thread execution).
        
        Args:
            prompt: Text prompt
        
        Returns:
            Generated text
        """
        try:
            model = self._get_model()
            response = model.generate_content(prompt)
            
            # Check if response has text attribute directly
            if hasattr(response, "text"):
                return response.text
            
            # Handle response object with parts structure
            if hasattr(response, "parts"):
                texts = []
                for part in response.parts:
                    if hasattr(part, "text"):
                        texts.append(part.text)
                return "".join(texts)
            
            # Fallback for dictionary-like response
            if isinstance(response, dict) and "text" in response:
                return response["text"]
            
            # Last resort, convert to string
            return str(response)
        except Exception as e:
            logger.exception(f"Error generating text with Gemini: {e}")
            return f"Error generating text with Gemini: {str(e)}"
    
    async def generate_with_image(self, prompt: str, image_path: str) -> str:
        """Generate text based on text and image.
        
        Args:
            prompt: Text prompt
            image_path: Path to image file
        
        Returns:
            Generated text
        """
        # Execute in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._generate_with_image_sync, prompt, image_path)
    
    def _generate_with_image_sync(self, prompt: str, image_path: str) -> str:
        """Generate text based on text and image synchronously.
        
        Args:
            prompt: Text prompt
            image_path: Path to image file
        
        Returns:
            Generated text
        """
        try:
            # Load image
            image_file = Path(image_path)
            if not image_file.exists():
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            with open(image_file, "rb") as f:
                image_bytes = f.read()
            
            # Create multimodal request
            model = self._get_model()
            response = model.generate_content([prompt, image_bytes])
            
            # Extract text from response
            if hasattr(response, "text"):
                return response.text
            
            if hasattr(response, "parts"):
                texts = []
                for part in response.parts:
                    if hasattr(part, "text"):
                        texts.append(part.text)
                return "".join(texts)
            
            return str(response)
        except Exception as e:
            logger.exception(f"Error generating with image using Gemini: {e}")
            return f"Error generating with image using Gemini: {str(e)}"
    
    async def generate_with_function_calling(self, 
                                           prompt: str, 
                                           functions: List[Dict[str, Any]]) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Generate text with function calling.
        
        Args:
            prompt: Text prompt
            functions: List of function definitions
        
        Returns:
            Tuple of (generated text, function call details if any)
        """
        # Execute in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._generate_with_function_calling_sync, prompt, functions)
    
    def _generate_with_function_calling_sync(self, 
                                           prompt: str, 
                                           functions: List[Dict[str, Any]]) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Generate text with function calling synchronously.
        
        Args:
            prompt: Text prompt
            functions: List of function definitions
        
        Returns:
            Tuple of (generated text, function call details if any)
        """
        try:
            model = self._get_model()
            
            # Create function declaration array for model
            tools = [{
                "function_declarations": functions
            }]
            
            # Generate response with function calling
            response = model.generate_content(
                prompt,
                tools=tools
            )
            
            # Extract text and function call
            text = ""
            function_call = None
            
            if hasattr(response, "text"):
                text = response.text
            
            if hasattr(response, "candidates"):
                for candidate in response.candidates:
                    if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                        for part in candidate.content.parts:
                            if hasattr(part, "text"):
                                text += part.text
                            if hasattr(part, "function_call"):
                                function_call = {
                                    "name": part.function_call.name,
                                    "args": part.function_call.args
                                }
            
            return text, function_call
        except Exception as e:
            logger.exception(f"Error generating with function calling using Gemini: {e}")
            return f"Error generating with function calling using Gemini: {str(e)}", None
    
    async def generate_chat(self, messages: List[Dict[str, str]]) -> str:
        """Generate text based on chat history.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
        
        Returns:
            Generated response text
        """
        # Execute in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._generate_chat_sync, messages)
    
    def _generate_chat_sync(self, messages: List[Dict[str, str]]) -> str:
        """Generate text based on chat history synchronously.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
        
        Returns:
            Generated response text
        """
        try:
            model = self._get_model()
            
            # Convert messages to chat format
            chat = model.start_chat()
            
            # Add all messages except the last one to history
            for message in messages[:-1]:
                role = message["role"]
                content = message["content"]
                
                if role == "user":
                    chat.send_message(content)
                elif role == "assistant":
                    # Can't directly add assistant messages in this API
                    # So we'll add it to the history in a different way
                    pass
            
            # Send the last message and get response
            last_message = messages[-1]
            response = chat.send_message(last_message["content"])
            
            if hasattr(response, "text"):
                return response.text
            
            if hasattr(response, "parts"):
                texts = []
                for part in response.parts:
                    if hasattr(part, "text"):
                        texts.append(part.text)
                return "".join(texts)
            
            return str(response)
        except Exception as e:
            logger.exception(f"Error generating chat response with Gemini: {e}")
            return f"Error generating chat response with Gemini: {str(e)}" 