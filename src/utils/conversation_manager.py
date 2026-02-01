"""
Gestionnaire de conversations pour le chatbot.
Sauvegarde et charge les historiques de conversations.
"""
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

class ConversationManager:
    """Gère les conversations multiples avec persistance."""
    
    def __init__(self, storage_dir: Path = None):
        if storage_dir is None:
            storage_dir = Path("data/conversations")
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.storage_dir / "index.json"
        
        # Charger ou créer l'index
        self._load_index()
    
    def _load_index(self):
        """Charge l'index des conversations."""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                self.index = json.load(f)
        else:
            self.index = {"conversations": []}
            self._save_index()
    
    def _save_index(self):
        """Sauvegarde l'index."""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
    
    def create_conversation(self, title: str = None) -> str:
        """
        Crée une nouvelle conversation.
        
        Returns:
            ID de la conversation
        """
        conv_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        if title is None:
            title = f"Conversation du {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        
        conversation = {
            "id": conv_id,
            "title": title,
            "created_at": timestamp,
            "updated_at": timestamp,
            "message_count": 0
        }
        
        self.index["conversations"].insert(0, conversation)
        self._save_index()
        
        # Créer le fichier de messages
        self._save_messages(conv_id, [])
        
        return conv_id
    
    def get_conversations(self) -> List[Dict[str, Any]]:
        """Retourne la liste des conversations."""
        return self.index["conversations"]
    
    def get_conversation(self, conv_id: str) -> Optional[Dict[str, Any]]:
        """Récupère une conversation par son ID."""
        for conv in self.index["conversations"]:
            if conv["id"] == conv_id:
                return conv
        return None
    
    def delete_conversation(self, conv_id: str) -> bool:
        """Supprime une conversation."""
        # Supprimer de l'index
        self.index["conversations"] = [
            c for c in self.index["conversations"] 
            if c["id"] != conv_id
        ]
        self._save_index()
        
        # Supprimer le fichier
        msg_file = self.storage_dir / f"{conv_id}.json"
        if msg_file.exists():
            msg_file.unlink()
            return True
        return False
    
    def update_title(self, conv_id: str, new_title: str):
        """Met à jour le titre d'une conversation."""
        for conv in self.index["conversations"]:
            if conv["id"] == conv_id:
                conv["title"] = new_title
                conv["updated_at"] = datetime.now().isoformat()
                self._save_index()
                return True
        return False
    
    def load_messages(self, conv_id: str) -> List[Dict[str, Any]]:
        """Charge les messages d'une conversation."""
        msg_file = self.storage_dir / f"{conv_id}.json"
        
        if msg_file.exists():
            with open(msg_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_messages(self, conv_id: str, messages: List[Dict[str, Any]]):
        """Sauvegarde les messages d'une conversation."""
        msg_file = self.storage_dir / f"{conv_id}.json"
        
        # Nettoyer les messages pour la sérialisation
        clean_messages = []
        for msg in messages:
            clean_msg = {
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg.get("timestamp", datetime.now().isoformat())
            }
            
            # Ajouter les métadonnées optionnelles
            if "sql" in msg:
                clean_msg["sql"] = msg["sql"]
            if "chart_type" in msg:
                clean_msg["chart_type"] = msg["chart_type"]
            if "data_preview" in msg:
                clean_msg["data_preview"] = msg["data_preview"]
            
            clean_messages.append(clean_msg)
        
        with open(msg_file, 'w', encoding='utf-8') as f:
            json.dump(clean_messages, f, ensure_ascii=False, indent=2)
    
    def add_message(self, conv_id: str, message: Dict[str, Any]):
        """Ajoute un message à une conversation."""
        messages = self.load_messages(conv_id)
        
        # Ajouter timestamp
        message["timestamp"] = datetime.now().isoformat()
        
        messages.append(message)
        self._save_messages(conv_id, messages)
        
        # Mettre à jour l'index
        for conv in self.index["conversations"]:
            if conv["id"] == conv_id:
                conv["updated_at"] = message["timestamp"]
                conv["message_count"] = len(messages)
                
                # Mettre à jour le titre si c'est le premier message utilisateur
                if len(messages) == 1 and message["role"] == "user":
                    # Titre basé sur le premier message
                    title = message["content"][:50]
                    if len(message["content"]) > 50:
                        title += "..."
                    conv["title"] = title
                
                self._save_index()
                break
    
    def clear_messages(self, conv_id: str):
        """Efface tous les messages d'une conversation."""
        self._save_messages(conv_id, [])
        
        # Mettre à jour l'index
        for conv in self.index["conversations"]:
            if conv["id"] == conv_id:
                conv["message_count"] = 0
                conv["updated_at"] = datetime.now().isoformat()
                self._save_index()
                break
    
    def set_session_context(self, conv_id: str, context_key: str, context_value: Any):
        """
        Stocke un contexte temporaire pour la session (disambiguation, etc.)
        
        Args:
            conv_id: ID conversation
            context_key: Clé (ex: 'awaiting_disambiguation')
            context_value: Valeur à stocker
        """
        
        # Créer fichier de contexte si n'existe pas
        context_file = self.storage_dir / f"{conv_id}_context.json"
        
        if context_file.exists():
            with open(context_file, 'r', encoding='utf-8') as f:
                context = json.load(f)
        else:
            context = {}
        
        context[context_key] = context_value
        
        with open(context_file, 'w', encoding='utf-8') as f:
            json.dump(context, f, ensure_ascii=False, indent=2)

    def get_session_context(self, conv_id: str, context_key: str) -> Optional[Any]:
        """Récupère un contexte de session"""
        
        context_file = self.storage_dir / f"{conv_id}_context.json"
        
        if not context_file.exists():
            return None
        
        with open(context_file, 'r', encoding='utf-8') as f:
            context = json.load(f)
        
        return context.get(context_key)

    def clear_session_context(self, conv_id: str, context_key: str = None):
        """Efface le contexte de session"""
        
        context_file = self.storage_dir / f"{conv_id}_context.json"
        
        if not context_file.exists():
            return
        
        if context_key is None:
            # Effacer tout
            context_file.unlink()
        else:
            # Effacer clé spécifique
            with open(context_file, 'r', encoding='utf-8') as f:
                context = json.load(f)
            
            if context_key in context:
                del context[context_key]
            
            with open(context_file, 'w', encoding='utf-8') as f:
                json.dump(context, f, ensure_ascii=False, indent=2)