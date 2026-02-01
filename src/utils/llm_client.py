"""
LLM Client - Wrapper unifié pour Ollama, Anthropic et OpenAI
Permet de basculer facilement entre les providers
"""
import os
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    """Client LLM unifié supportant Ollama, Anthropic et OpenAI"""
    
    def __init__(self, provider: Optional[str] = None):
        """
        Initialize LLM client.
        
        Args:
            provider: 'ollama' | 'anthropic' | 'openai'. If None, uses LLM_PROVIDER from .env
        """
        self.provider = provider or os.getenv('LLM_PROVIDER', 'ollama').lower()
        
        if self.provider == 'ollama':
            self._init_ollama()
        elif self.provider == 'anthropic':
            self._init_anthropic()
        elif self.provider == 'openai':
            self._init_openai()
        else:
            raise ValueError(
                f"Provider '{self.provider}' non supporté. "
                f"Utilisez 'ollama', 'anthropic' ou 'openai'"
            )
    
    def _init_ollama(self):
        """Initialize Ollama client"""
        try:
            import ollama
            self.client = ollama
            self.model = os.getenv('OLLAMA_MODEL', 'llama3.1')
            self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            print(f"✅ Ollama initialisé avec le modèle: {self.model}")
        except ImportError:
            raise ImportError(
                "Le package 'ollama' n'est pas installé. "
                "Installez-le avec: pip install ollama"
            )
    
    def _init_anthropic(self):
        """Initialize Anthropic client"""
        try:
            from anthropic import Anthropic
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY non trouvée dans .env")
            self.client = Anthropic(api_key=api_key)
            self.model = os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')
            print(f"✅ Anthropic initialisé avec le modèle: {self.model}")
        except ImportError:
            raise ImportError(
                "Le package 'anthropic' n'est pas installé. "
                "Installez-le avec: pip install anthropic"
            )
    
    def _init_openai(self):
        """Initialize OpenAI/OpenRouter client"""
        try:
            from openai import OpenAI
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY non trouvée dans .env")
            
            # Support OpenRouter
            base_url = os.getenv('OPENAI_BASE_URL', None)
            if base_url:
                self.client = OpenAI(api_key=api_key, base_url=base_url)
                print(f"✅ OpenRouter initialisé")
            else:
                self.client = OpenAI(api_key=api_key)
                print(f"✅ OpenAI initialisé")
            
            self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
            print(f"🤖 Modèle: {self.model}")
        except ImportError:
            raise ImportError(
                "Le package 'openai' n'est pas installé. "
                "Installez-le avec: pip install openai"
            )
    
    def create_message(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.3,
        system: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a message using the configured provider.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)
            system: Optional system prompt
        
        Returns:
            Dict with 'content' key containing response text
        """
        if self.provider == 'ollama':
            return self._ollama_message(messages, max_tokens, temperature, system)
        elif self.provider == 'openai':
            return self._openai_message(messages, max_tokens, temperature, system)
        else:
            return self._anthropic_message(messages, max_tokens, temperature, system)
    
    def _ollama_message(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        system: Optional[str]
    ) -> Dict[str, Any]:
        """Create message using Ollama"""
        
        # Préparer les messages pour Ollama
        ollama_messages = []
        
        # Ajouter le system prompt si présent
        if system:
            ollama_messages.append({
                'role': 'system',
                'content': system
            })
        
        # Ajouter les messages utilisateur
        ollama_messages.extend(messages)
        
        try:
            response = self.client.chat(
                model=self.model,
                messages=ollama_messages,
                options={
                    'temperature': temperature,
                    'num_predict': max_tokens,
                }
            )
            
            # Format compatible avec Anthropic
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': response['message']['content']
                    }
                ],
                'model': self.model,
                'usage': {
                    'input_tokens': response.get('prompt_eval_count', 0),
                    'output_tokens': response.get('eval_count', 0)
                }
            }
        
        except Exception as e:
            raise Exception(f"Erreur Ollama: {str(e)}")
    
    def _openai_message(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        system: Optional[str]
    ) -> Dict[str, Any]:
        """Create message using OpenAI"""
        
        # Préparer les messages pour OpenAI
        openai_messages = []
        
        # Ajouter le system prompt si présent
        if system:
            openai_messages.append({
                'role': 'system',
                'content': system
            })
        
        # Ajouter les messages utilisateur
        openai_messages.extend(messages)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # Format compatible avec Anthropic
            return {
                'content': [
                    {
                        'type': 'text',
                        'text': response.choices[0].message.content
                    }
                ],
                'model': self.model,
                'usage': {
                    'input_tokens': response.usage.prompt_tokens,
                    'output_tokens': response.usage.completion_tokens
                }
            }
        
        except Exception as e:
            raise Exception(f"Erreur OpenAI: {str(e)}")
    
    def _anthropic_message(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        system: Optional[str]
    ) -> Dict[str, Any]:
        """Create message using Anthropic"""
        
        kwargs = {
            'model': self.model,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'messages': messages
        }
        
        if system:
            kwargs['system'] = system
        
        try:
            response = self.client.messages.create(**kwargs)
            return response
        
        except Exception as e:
            raise Exception(f"Erreur Anthropic: {str(e)}")
    
    def get_provider_info(self) -> Dict[str, str]:
        """Get information about the current provider"""
        return {
            'provider': self.provider,
            'model': self.model,
            'status': '✅ Connecté'
        }


def test_llm_client():
    """Test du client LLM"""
    
    print("="*70)
    print("🧪 TEST LLM CLIENT")
    print("="*70)
    
    try:
        # Initialiser le client
        client = LLMClient()
        
        # Afficher les infos
        info = client.get_provider_info()
        print(f"\n📊 Provider: {info['provider']}")
        print(f"🤖 Model: {info['model']}")
        print(f"✅ Status: {info['status']}")
        
        # Test simple
        print("\n🔍 Test de génération...")
        
        response = client.create_message(
            messages=[
                {
                    'role': 'user',
                    'content': 'Réponds en une phrase : Qu\'est-ce que la démocratie ?'
                }
            ],
            max_tokens=100,
            temperature=0.3
        )
        
        result_text = response['content'][0]['text']
        print(f"\n💬 Réponse: {result_text}")
        
        print("\n✅ Test réussi !")
        
    except Exception as e:
        print(f"\n❌ Erreur: {str(e)}")
        print("\n💡 Vérifiez que:")
        print("   1. Le provider est correctement configuré dans .env")
        print("   2. Les dépendances sont installées (pip install ollama/anthropic/openai)")
        print("   3. Le service est démarré (pour Ollama: ollama serve)")


if __name__ == "__main__":
    test_llm_client()