"""
Script de test pour vérifier la configuration LLM (Ollama, Anthropic ou OpenAI)
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

load_dotenv()


def test_ollama():
    """Test la connexion Ollama"""
    print("\n" + "="*70)
    print("🧪 TEST OLLAMA")
    print("="*70)
    
    try:
        import requests
        
        base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        model = os.getenv('OLLAMA_MODEL', 'llama3.1')
        
        print(f"📡 Base URL: {base_url}")
        print(f"🤖 Model: {model}")
        
        # Test 1: Vérifier que Ollama est démarré
        print("\n1️⃣ Vérification du serveur Ollama...")
        try:
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                print("   ✅ Ollama est démarré")
                models = response.json().get('models', [])
                print(f"   📦 Modèles disponibles: {len(models)}")
                for m in models:
                    print(f"      - {m['name']}")
            else:
                print(f"   ❌ Erreur HTTP {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("   ❌ Ollama n'est pas démarré !")
            print("   💡 Lance : ollama serve")
            return False
        
        # Test 2: Vérifier que le modèle est téléchargé
        print(f"\n2️⃣ Vérification du modèle {model}...")
        model_exists = any(m['name'] == model for m in models)
        if model_exists:
            print(f"   ✅ Modèle {model} disponible")
        else:
            print(f"   ❌ Modèle {model} non trouvé")
            print(f"   💡 Lance : ollama pull {model}")
            return False
        
        # Test 3: Test de génération
        print("\n3️⃣ Test de génération...")
        from src.utils.llm_client import LLMClient
        
        client = LLMClient()
        response = client.create_message(
            messages=[{"role": "user", "content": "Dis bonjour en une phrase"}],
            max_tokens=50
        )
        
        if response and 'content' in response:
            text = response['content'][0]['text']
            print(f"   ✅ Génération réussie : {text[:100]}")
            return True
        else:
            print("   ❌ Génération échouée")
            return False
            
    except Exception as e:
        print(f"   ❌ Erreur : {e}")
        return False


def test_anthropic():
    """Test la connexion Anthropic"""
    print("\n" + "="*70)
    print("🧪 TEST ANTHROPIC")
    print("="*70)
    
    try:
        api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not api_key:
            print("❌ ANTHROPIC_API_KEY non trouvé dans .env")
            return False
        
        print(f"🔑 API Key: {api_key[:20]}...")
        
        print("\n1️⃣ Test de connexion...")
        from src.utils.llm_client import LLMClient
        
        client = LLMClient()
        response = client.create_message(
            messages=[{"role": "user", "content": "Dis bonjour en une phrase"}],
            max_tokens=50
        )
        
        if response and 'content' in response:
            text = response['content'][0]['text']
            print(f"   ✅ Génération réussie : {text[:100]}")
            return True
        else:
            print("   ❌ Génération échouée")
            return False
            
    except Exception as e:
        error_msg = str(e)
        
        if 'credit balance' in error_msg.lower():
            print("   ❌ ERREUR : Crédits insuffisants")
            print("   💡 Solutions :")
            print("      1. Ajouter des crédits sur https://console.anthropic.com/settings/billing")
            print("      2. OU passer à OpenAI : LLM_PROVIDER=openai dans .env")
            print("      3. OU passer à Ollama (gratuit) : LLM_PROVIDER=ollama dans .env")
        else:
            print(f"   ❌ Erreur : {e}")
        
        return False


def test_openai():
    """Test la connexion OpenAI"""
    print("\n" + "="*70)
    print("🧪 TEST OPENAI")
    print("="*70)
    
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            print("❌ OPENAI_API_KEY non trouvée dans .env")
            return False
        
        print(f"🔑 API Key: {api_key[:20]}...")
        model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        print(f"🤖 Model: {model}")
        
        print("\n1️⃣ Test de connexion...")
        from src.utils.llm_client import LLMClient
        
        client = LLMClient()
        response = client.create_message(
            messages=[{"role": "user", "content": "Dis bonjour en une phrase"}],
            max_tokens=50
        )
        
        if response and 'content' in response:
            text = response['content'][0]['text']
            print(f"   ✅ Génération réussie : {text[:100]}")
            return True
        else:
            print("   ❌ Génération échouée")
            return False
            
    except Exception as e:
        error_msg = str(e)
        
        if 'api key' in error_msg.lower() or 'authentication' in error_msg.lower():
            print("   ❌ ERREUR : Clé API invalide")
            print("   💡 Vérifiez votre OPENAI_API_KEY sur https://platform.openai.com/api-keys")
        elif 'quota' in error_msg.lower() or 'billing' in error_msg.lower():
            print("   ❌ ERREUR : Quota dépassé ou facturation requise")
            print("   💡 Ajoutez des crédits sur https://platform.openai.com/account/billing")
        else:
            print(f"   ❌ Erreur : {e}")
        
        return False


def main():
    """Point d'entrée principal"""
    
    print("="*70)
    print("🔍 DIAGNOSTIC CONFIGURATION LLM")
    print("="*70)
    
    # Charger .env
    load_dotenv()
    provider = os.getenv('LLM_PROVIDER', 'ollama')
    
    print(f"\n📋 Provider configuré : {provider.upper()}")
    
    # Test selon le provider
    if provider == 'ollama':
        success = test_ollama()
    elif provider == 'anthropic':
        success = test_anthropic()
    elif provider == 'openai':
        success = test_openai()
    else:
        print(f"❌ Provider inconnu : {provider}")
        print("💡 Providers supportés : ollama, anthropic, openai")
        success = False
    
    # Résumé final
    print("\n" + "="*70)
    if success:
        print("✅ CONFIGURATION OK - Tout fonctionne !")
        print("🚀 Tu peux lancer l'application :")
        print("   streamlit run src/app/streamlit_app.py")
    else:
        print("❌ CONFIGURATION INCORRECTE")
        print("\n💡 SOLUTIONS :")
        print("\n1️⃣ Pour utiliser Ollama (GRATUIT) :")
        print("   a) Installer : https://ollama.ai/download")
        print("   b) Lancer : ollama serve")
        print("   c) Télécharger : ollama pull qwen2.5:14b")
        print("   d) .env : LLM_PROVIDER=ollama")
        print("\n2️⃣ Pour utiliser OpenAI :")
        print("   a) Créer clé : https://platform.openai.com/api-keys")
        print("   b) Ajouter crédits : https://platform.openai.com/account/billing")
        print("   c) .env : LLM_PROVIDER=openai")
        print("   d) .env : OPENAI_API_KEY=sk-proj-...")
        print("\n3️⃣ Pour utiliser Anthropic (Claude) :")
        print("   a) Ajouter crédits : https://console.anthropic.com/settings/billing")
        print("   b) .env : LLM_PROVIDER=anthropic")
        print("   c) .env : ANTHROPIC_API_KEY=sk-ant-...")
    print("="*70)


if __name__ == "__main__":
    main()