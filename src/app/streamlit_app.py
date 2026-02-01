"""
Application Streamlit - Version Professionnelle V3 avec Traçabilité
Design moderne avec intelligence complète + monitoring
✅ FIXED: Gestion correcte du state lors des changements de conversation/métriques
"""
import streamlit as st
import sys
import time
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from typing import Dict, Any
import pandas as pd
import re


# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agent.sql_generator import SQLGenerator
from src.agent.query_validator import QueryValidator
from src.agent.query_executor import QueryExecutor
from src.agent.response_generator import ResponseGenerator
from src.agent.intent_classifier import IntentClassifier
from src.agent.fraud_analyzer import FraudAnalyzer
from src.utils.conversation_manager import ConversationManager
from src.utils.config import DB_PATH
from src.monitoring.tracer import TracerManager, RequestTracer
from src.agent.disambiguator import Disambiguator
from src.utils.cache_manager import CacheManager

# Configuration
st.set_page_config(
    page_title="Élections 2025 - Côte d'Ivoire",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Ultra-Moderne + ✅ FIX CONVERSATION DESIGN
st.markdown("""
<style>
    /* Variables */
    :root {
        --primary: #FF7A00;
        --secondary: #009E60;
        --dark: #1a1a1a;
        --light: #f8f9fa;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
    }
    
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FF7A00 0%, #009E60 100%);
        padding: 2rem 1rem;
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: white !important;
        font-weight: 700;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* ✅ FIX: Boutons conversation - Texte FONCÉ sur fond clair */
    [data-testid="stSidebar"] button {
        background: rgba(255,255,255,0.2) !important;
        border: 1px solid rgba(255,255,255,0.3) !important;
        border-radius: 12px !important;
        padding: 0.75rem 1rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        backdrop-filter: blur(10px) !important;
        color: white !important;  /* ✅ Texte blanc par défaut */
    }
    
    [data-testid="stSidebar"] button:hover {
        background: rgba(255,255,255,0.3) !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
    }
    
    /* ✅ FIX: Bouton conversation ACTIVE - Texte FONCÉ sur fond BLANC */
    [data-testid="stSidebar"] button[kind="primary"] {
        background: white !important;
        color: #FF7A00 !important;  /* ✅ Texte orange sur fond blanc */
        border: 2px solid white !important;
        font-weight: 700 !important;
    }
    
    /* ✅ FIX: Forcer le texte foncé sur bouton primary */
    [data-testid="stSidebar"] button[kind="primary"] p {
        color: #FF7A00 !important;  /* ✅ Force orange */
    }
    
    .main .block-container {
        max-width: 1400px;
        padding: 2rem 2rem 4rem 2rem;
    }
    
    .custom-header {
        background: linear-gradient(135deg, #FF7A00 0%, #009E60 100%);
        padding: 2.5rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(255, 122, 0, 0.2);
        text-align: center;
    }
    
    .custom-header h1 {
        color: white;
        font-size: 3rem;
        font-weight: 800;
        margin: 0;
        text-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }
    
    .custom-header p {
        color: rgba(255,255,255,0.95);
        font-size: 1.2rem;
        margin: 0.5rem 0 0 0;
        font-weight: 500;
    }
    
    .stChatMessage {
        border-radius: 16px !important;
        padding: 1.5rem !important;
        margin-bottom: 1rem !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
        backdrop-filter: blur(10px);
    }
    
    .stChatMessage[data-testid*="user"] {
        background: linear-gradient(135deg, #FF7A00 0%, #FF9E3D 100%) !important;
        color: white !important;
        margin-left: 20%;
    }
    
    .stChatMessage[data-testid*="assistant"] {
        background: white !important;
        border: 1px solid #e5e7eb !important;
        margin-right: 20%;
    }
    
    .stChatInputContainer {
        border-top: 2px solid #e5e7eb;
        padding-top: 1.5rem;
        background: linear-gradient(to top, rgba(255,255,255,0.95), transparent);
        backdrop-filter: blur(10px);
    }
    
    .stDataFrame {
        border-radius: 12px !important;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
        border: 1px solid #e5e7eb !important;
    }
    
    .js-plotly-plot {
        border-radius: 16px !important;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08) !important;
        overflow: hidden;
        border: 1px solid #e5e7eb;
    }
    
    .streamlit-expanderHeader {
        border-radius: 12px !important;
        background: linear-gradient(135deg, #f8f9fa 0%, #e5e7eb 100%) !important;
        font-weight: 600 !important;
        padding: 1rem !important;
        border: 1px solid #e5e7eb !important;
    }
    
    .streamlit-expanderHeader:hover {
        background: linear-gradient(135deg, #e5e7eb 0%, #cbd5e1 100%) !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    .stDownloadButton button {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3) !important;
    }
    
    .stDownloadButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(16, 185, 129, 0.4) !important;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 800 !important;
        background: linear-gradient(135deg, #FF7A00, #009E60);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .stAlert {
        border-radius: 12px !important;
        border-left: 4px solid #FF7A00 !important;
        padding: 1rem !important;
    }
    
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #FF7A00, #009E60);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, #009E60, #FF7A00);
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .stChatMessage {
        animation: fadeIn 0.3s ease-out;
    }
    
    .badge {
        display: inline-block;
        padding: 0.35rem 0.75rem;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 0.25rem;
    }
    
    .badge-success {
        background: #10b981;
        color: white;
    }
    
    .badge-warning {
        background: #f59e0b;
        color: white;
    }
    
    .badge-danger {
        background: #ef4444;
        color: white;
    }
    
    .badge-info {
        background: #3b82f6;
        color: white;
    }
            
    .disambiguation-box {
        background: linear-gradient(135deg, #fff7ed 0%, #fed7aa 100%);
        border-left: 4px solid #f59e0b;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 12px rgba(245, 158, 11, 0.15);
    }
    
    .disambiguation-box h4 {
        color: #ea580c;
        margin-bottom: 1rem;
        font-weight: 700;
    }
    
    .disambiguation-option {
        background: white;
        border: 2px solid #fed7aa;
        border-radius: 8px;
        padding: 0.75rem;
        margin: 0.5rem 0;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .disambiguation-option:hover {
        border-color: #f59e0b;
        transform: translateX(5px);
        box-shadow: 0 2px 8px rgba(245, 158, 11, 0.2);
    }
</style>
""", unsafe_allow_html=True)


def reset_conversation_state():
    """
    ✅ NOUVELLE FONCTION: Réinitialise TOUS les flags de conversation
    À appeler lors de :
    - Changement de conversation
    - Nouvelle conversation
    - Changement vers métriques
    - Retour des métriques
    """
    st.session_state.processing = False
    st.session_state.awaiting_disambiguation = False
    st.session_state.disambiguation_info = None
    st.session_state.original_question = None
    st.session_state.should_reprocess = False
    st.session_state.should_reprocess_active = False
    st.session_state.should_reprocess_done = False


def init_session_state():
    """Initialise l'état de la session avec tous les composants + tracer"""
    
    if 'initialized' not in st.session_state:
        try:
            # Composants de base
            st.session_state.sql_generator = SQLGenerator()
            st.session_state.cache_manager = CacheManager()
            st.session_state.query_validator = QueryValidator(max_limit=1000)
            st.session_state.query_executor = QueryExecutor(DB_PATH)
            st.session_state.response_generator = ResponseGenerator()
            
            # Composants intelligents
            st.session_state.intent_classifier = IntentClassifier()
            st.session_state.fraud_analyzer = FraudAnalyzer()
            st.session_state.disambiguator = Disambiguator()
            
            st.session_state.conversation_manager = ConversationManager()
            st.session_state.query_executor.connect()
            
            # Tracer Manager
            st.session_state.tracer_manager = TracerManager()
            
            st.session_state.app_ready = True
            
        except Exception as e:
            st.session_state.app_ready = False
            st.session_state.error_message = str(e)
        
        st.session_state.initialized = True
    
    # ✅ AU LIEU DE créer systématiquement une nouvelle conversation
    if 'current_conversation_id' not in st.session_state:
        conversations = st.session_state.conversation_manager.get_conversations()
        
        if conversations:
            # Réutiliser la plus récente
            st.session_state.current_conversation_id = conversations[0]['id']
        else:
            # Créer UNIQUEMENT si aucune n'existe
            conv_id = st.session_state.conversation_manager.create_conversation()
            st.session_state.current_conversation_id = conv_id
    
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    if 'show_metrics' not in st.session_state:
        st.session_state.show_metrics = False
    if 'awaiting_disambiguation' not in st.session_state:
        st.session_state.awaiting_disambiguation = False
    if 'disambiguation_info' not in st.session_state:
        st.session_state.disambiguation_info = None
    if 'original_question' not in st.session_state:
        st.session_state.original_question = None


def create_chart(data: pd.DataFrame, chart_type: str, question: str):
    """Crée un graphique moderne"""
    
    if data.empty or len(data) == 0:
        return None
    
    cols = data.columns.tolist()
    data_plot = data.head(30).copy()  # ✅ AJOUT .copy()
    
    # ✅ NOUVEAU : Filtrer les NaN avant Plotly
    if chart_type in ['bar', 'auto', 'histogram']:
        # Pour histogrammes, on a besoin de valeurs numériques
        y_col = cols[1] if len(cols) > 1 else cols[0]
        
        # Vérifier si la colonne Y contient des valeurs numériques
        if y_col in data_plot.columns:
            # ✅ DEBUG
            #print(f"   📊 Histogramme - Colonne Y: '{y_col}'")
            #print(f"   📊 Type: {data_plot[y_col].dtype}")
            
            # Vérifier que c'est numérique
            if not pd.api.types.is_numeric_dtype(data_plot[y_col]):
                #print(f"   ⚠️  Colonne '{y_col}' n'est pas numérique, essai colonne suivante...")
                # Chercher la première colonne numérique
                numeric_cols = data_plot.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    y_col = numeric_cols[0]
                    #print(f"   ✅ Utilisation de '{y_col}' à la place")
                else:
                    print(f"   ❌ Aucune colonne numérique trouvée!")
                    return None
            
            # Filtrer les NaN
            data_plot = data_plot.dropna(subset=[y_col])
            
            # Si toutes les valeurs sont NaN, retourner None
            if data_plot.empty:
                #print(f"   ⚠️  Graphique impossible : colonne '{y_col}' ne contient que des NaN")
                return None
    
    elif chart_type == 'pie':
        # Pour camembert, on a besoin de valeurs numériques
        values_col = cols[1] if len(cols) > 1 else cols[0]
        
        if values_col in data_plot.columns:
            # ✅ DEBUG
            #print(f"   🥧 Camembert - Colonne valeurs: '{values_col}'")
            #print(f"   🥧 Type colonne: {data_plot[values_col].dtype}")
            
            # Vérifier que c'est numérique
            if not pd.api.types.is_numeric_dtype(data_plot[values_col]):
                #print(f"   ⚠️  Colonne '{values_col}' n'est pas numérique, essai colonne suivante...")
                # Chercher la première colonne numérique
                numeric_cols = data_plot.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    values_col = numeric_cols[0]
                    #print(f"   ✅ Utilisation de '{values_col}' à la place")
                else:
                    print(f"   ❌ Aucune colonne numérique trouvée!")
                    return None
            
            # Filtrer les NaN
            data_plot = data_plot.dropna(subset=[values_col])
            
            if data_plot.empty:
                print(f"   ⚠️  Graphique impossible : colonne '{values_col}' ne contient que des NaN")
                return None
    
    try:
        if chart_type in ['bar', 'auto', 'histogram']:
            x_col = cols[0]
            y_col = cols[1] if len(cols) > 1 else cols[0]
            
            # ✅ Vérifier encore une fois que y_col est numérique
            if not pd.api.types.is_numeric_dtype(data_plot[y_col]):
                numeric_cols = data_plot.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    y_col = numeric_cols[0]
            
            fig = px.bar(
                data_plot,
                x=x_col,
                y=y_col,
                text=y_col,
                labels={
                    x_col: x_col.replace('_', ' ').title(), 
                    y_col: y_col.replace('_', ' ').title()
                },
                color=y_col,
                color_continuous_scale='RdYlGn',
                template='plotly_white',
                title=f"📊 {question[:80]}"
            )
            fig.update_traces(
                texttemplate='%{text:,.0f}',
                textposition='outside',
                textfont=dict(size=13, family="Inter", color='#1a1a1a')
            )
            fig.update_xaxes(tickangle=45)
            fig.update_layout(
                height=550,
                showlegend=False,
                margin=dict(l=20, r=20, t=60, b=20),
                font=dict(family="Inter, sans-serif", size=12),
                title_font=dict(size=16, color='#1a1a1a', family="Inter")
            )
            return fig
        
        elif chart_type == 'pie':
            names_col = cols[0]
            values_col = cols[1] if len(cols) > 1 else cols[0]
            
            # ✅ Vérifier que values_col est numérique
            if not pd.api.types.is_numeric_dtype(data_plot[values_col]):
                numeric_cols = data_plot.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    values_col = numeric_cols[0]
            
            data_pie = data_plot.head(15)
            
            fig = px.pie(
                data_pie,
                names=names_col,
                values=values_col,
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Oranges_r,
                template='plotly_white',
                title=f"📊 {question[:80]}"
            )
            fig.update_layout(
                height=550,
                margin=dict(l=20, r=20, t=60, b=20),
                font=dict(family="Inter, sans-serif"),
                title_font=dict(size=16, color='#1a1a1a', family="Inter")
            )
            return fig
        
        elif chart_type == 'line':
            x_col = cols[0]
            y_col = cols[1] if len(cols) > 1 else cols[0]
            
            fig = px.line(
                data_plot,
                x=x_col,
                y=y_col,
                markers=True,
                template='plotly_white',
                title=f"📊 {question[:80]}"
            )
            fig.update_traces(line_color='#FF7A00', line_width=3, marker=dict(size=8))
            fig.update_layout(
                height=550,
                margin=dict(l=20, r=20, t=60, b=20),
                font=dict(family="Inter, sans-serif"),
                title_font=dict(size=16, color='#1a1a1a', family="Inter")
            )
            return fig
        
    except Exception as e:
        print(f"   ❌ Erreur création graphique: {e}")
        return None
    
    return None


def handle_conversation(question: str) -> str:
    """Gère les questions conversationnelles"""
    
    q_lower = question.lower()
    
    if any(word in q_lower for word in ['bonjour', 'salut', 'hello', 'hi', 'bonsoir']):
        return """👋 **Bonjour !**

Je suis votre assistant IA pour les élections législatives 2025 de Côte d'Ivoire.

**🎯 Mes capacités :**
- 📊 Consulter les résultats (partis, régions, circonscriptions)
- 🔍 Analyser les taux de participation
- 🚨 Détecter les anomalies et incohérences
- 📈 Créer des visualisations interactives

**💡 Exemples de questions :**
- "Combien de sièges a gagné le RHDP ?"
- "Y a-t-il eu des fraudes ?"
- "Top 10 des candidats"
- "Circonscriptions avec participation anormale"

**Posez-moi vos questions !** 🗳️"""
    
    elif any(word in q_lower for word in ['merci', 'thank', 'cool', 'super', 'génial']):
        return "😊 **De rien !** N'hésitez pas pour d'autres questions."
    
    elif any(word in q_lower for word in ['comment', 'fonctionne', 'aide', 'help']):
        return """ℹ️ **Comment je fonctionne :**

**1. Questions factuelles** → Requêtes SQL automatiques
   - Ex: "Résultats du PDCI-RDA"

**2. Détection de fraude** → Analyses mathématiques
   - Ex: "Y a-t-il des incohérences ?"

**3. Visualisations** → Graphiques sur demande
   - Ex: "Graphique des sièges par parti"

**Sources :** Base de données officielle CEI

**Que voulez-vous savoir ?** 🤔"""
    
    return "💬 Posez-moi une question sur les élections 2025 !"


def handle_off_topic(question: str) -> str:
    """Gère les questions hors sujet"""
    
    return f"""🤔 **Question hors sujet**

"{question}" ne concerne pas les élections 2025 de Côte d'Ivoire.

**Je peux vous aider avec :**
- ✅ Résultats électoraux
- ✅ Analyses de participation
- ✅ Détection d'anomalies
- ✅ Visualisations de données

**Reformulez votre question !** 🗳️"""


def _handle_sql_query_traced(question: str, tracer: RequestTracer):
    """Gère requête SQL AVEC TRAÇABILITÉ"""
    
    # 1. Détecter demande de graphique
    # ❌ DÉPRÉCIÉ : Utilise la détection de intent_classifier à la place
    # chart_request = st.session_state.response_generator.detect_chart_request(question)
    chart_request = {"requested": False, "type": None}  # Sera écrasé par intent_classifier
    
    # 2. Générer SQL
    start_time = time.time()
    sql_result = st.session_state.sql_generator.generate_sql(question)
    duration_ms = (time.time() - start_time) * 1000
    
    # Log LLM call
    tracer.log_llm_call(
        model='llama3.1',
        tokens_input=sql_result.get('tokens_input', 150),
        tokens_output=sql_result.get('tokens_output', 100),
        duration_ms=duration_ms
    )
    
    if not sql_result['success']:
        tracer.log_error('sql_generation', sql_result.get('error', 'Erreur génération SQL'))
        return {"success": False, "error": sql_result.get('error', 'Erreur génération SQL')}
    
    sql = sql_result['sql']
    
    # 3. Valider SQL
    start_time = time.time()
    validation = st.session_state.query_validator.validate(sql)
    duration_ms = (time.time() - start_time) * 1000
    tracer.log_step('sql_validation', {'valid': validation['valid']}, duration_ms)
    
    if not validation['valid']:
        tracer.log_error('sql_validation', "Requête non autorisée")
        return {"success": False, "error": "Requête non autorisée"}
    
    sql = validation['sanitized_sql']
    
    # 4. Exécuter SQL
    start_time = time.time()
    result = st.session_state.query_executor.execute(sql)
    duration_ms = (time.time() - start_time) * 1000
    
    # Log SQL execution
    tracer.log_sql_query(
        sql=sql,
        result_rows=len(result['data']) if result['success'] else 0,
        duration_ms=duration_ms,
        success=result['success']
    )
    
    if not result['success']:
        tracer.log_error('sql_execution', result.get('error', 'Erreur exécution'))
        return {"success": False, "error": result.get('error', 'Erreur exécution')}
    
    data = result['data']
    if data.empty:
        tracer.log_business_error(
            error_type='empty_result',
            description="Requête SQL exécutée mais aucun résultat trouvé",
            sql=sql
        )
        
        return {
            "success": False,
            "error": "Aucun résultat trouvé dans la base de données."
        }
    
    # 5. Générer réponse
    start_time = time.time()
    response_result = st.session_state.response_generator.generate_response(
        question=question,
        data=data,
        sql=sql,
        needs_chart=chart_request['requested']
    )
    duration_ms = (time.time() - start_time) * 1000
    
    # Log appel LLM pour réponse
    tracer.log_llm_call(
        model='llama3.1',
        tokens_input=response_result.get('tokens_input', 200),
        tokens_output=response_result.get('tokens_output', 150),
        duration_ms=duration_ms
    )
    
    if not response_result['success']:
        return {"success": False, "error": response_result['response']}

    # Extraire les pages citées
    pages_cited = response_result.get('pages_cited', [])

    return {
        "success": True,
        "response": response_result['response'],
        "data": data,
        "sql": sql,
        "chart_request": chart_request,
        "row_count": len(data),
        "intent": "sql_query",
        "pages_cited": pages_cited
    }


def _handle_fraud_analysis_traced(question: str, tracer: RequestTracer):
    """Gère analyse de fraude AVEC TRAÇABILITÉ"""
    
    start_time = time.time()
    fraud_result = st.session_state.fraud_analyzer.analyze(question)
    duration_ms = (time.time() - start_time) * 1000
    
    # Log fraud analysis
    tracer.log_fraud_analysis(
        anomalies_found=len(fraud_result.get('results', [])) if fraud_result.get('success') else 0,
        analysis_type=fraud_result.get('analysis_type', 'unknown'),
        duration_ms=duration_ms
    )
    
    if not fraud_result.get('success'):
        tracer.log_error('fraud_analysis', fraud_result.get('error', 'Analysis failed'))
    
    response_text = fraud_result['summary']
    
    if fraud_result.get('recommendations'):
        response_text += "\n\n**📋 Recommandations :**\n"
        for rec in fraud_result['recommendations']:
            response_text += f"- {rec}\n"
    
    return {
        "success": True,
        "response": response_text,
        "data": fraud_result.get('results'),
        "intent": "fraud_analysis",
        "anomalies_found": fraud_result.get('anomalies_found', 0)
    }


def _handle_chart_traced(question: str, tracer: RequestTracer):
    """Gère génération de graphique AVEC TRAÇABILITÉ"""
    
    q_lower = question.lower()
    
    # Détection type de graphique
    if any(kw in q_lower for kw in ['camembert', 'pie', 'secteurs', 'circulaire', 'diagramme circulaire', 'diagramme en secteurs']):
        chart_type = 'pie'
    elif any(kw in q_lower for kw in ['courbe', 'line', 'évolution']):
        chart_type = 'line'
    else:
        chart_type = 'bar'
    
    # Créer question SQL-friendly
    sql_question = question
    
    chart_keywords = [
        'fait un', 'fais un', 'crée un', 'génère un', 'montre un',
        'graphique', 'histogramme', 'diagramme', 'courbe', 'camembert',
        'chart', 'visualisation', 'visualise', 'barres', 'secteurs',
        'circulaire', 'pie', 'line', 'bar'
    ]
    
    for kw in chart_keywords:
        sql_question = re.sub(rf'\b{re.escape(kw)}\b', '', sql_question, flags=re.IGNORECASE)
    
    sql_question = ' '.join(sql_question.split()).strip()
    
    if not sql_question or len(sql_question) < 5:
        match = re.search(r'(?:candidat|parti|voix|participation|résultat).*(?:de|à|dans)\s+([A-ZÀ-Ÿ][a-zà-ÿ\-]+)', question, re.IGNORECASE)
        
        if match:
            entity = match.group(1)
            
            if 'candidat' in q_lower:
                sql_question = f"liste des candidats de {entity} avec leurs voix"
            elif 'parti' in q_lower:
                sql_question = f"résultats des partis à {entity}"
            else:
                sql_question = f"résultats à {entity}"
        else:
            sql_question = "top 10 des candidats par nombre de voix"
    
    # Générer SQL
    start_time = time.time()
    sql_result = st.session_state.sql_generator.generate_sql(sql_question)
    duration_ms = (time.time() - start_time) * 1000
    
    tracer.log_llm_call(
        model='llama3.1',
        tokens_input=sql_result.get('tokens_input', 150),
        tokens_output=sql_result.get('tokens_output', 100),
        duration_ms=duration_ms
    )
    
    if not sql_result['success']:
        tracer.log_error('chart_sql_generation', sql_result.get('error', 'Erreur génération SQL'))
        return {"success": False, "error": "Impossible de générer le graphique"}
    
    sql = sql_result['sql']
    
    # Valider
    start_time = time.time()
    validation = st.session_state.query_validator.validate(sql)
    duration_ms = (time.time() - start_time) * 1000
    tracer.log_step('sql_validation', {'valid': validation['valid']}, duration_ms)
    
    if not validation['valid']:
        tracer.log_error('chart_sql_validation', "Requête non autorisée")
        return {"success": False, "error": "Requête non autorisée"}
    
    sql = validation['sanitized_sql']
    
    # Optimiser pour graphiques
    if 'LIMIT' in sql.upper():
        sql = re.sub(r'LIMIT\s+\d+', 'LIMIT 30', sql, flags=re.IGNORECASE)
    else:
        sql += ' LIMIT 30'
    
    # Exécuter
    start_time = time.time()
    result = st.session_state.query_executor.execute(sql)
    duration_ms = (time.time() - start_time) * 1000

    # ✅ FIX CRITIQUE : Vérifier succès AVANT d'utiliser data
    if not result['success']:
        tracer.log_error('chart_sql_execution', result.get('error', 'Erreur exécution'))
        return {"success": False, "error": "Erreur lors de l'exécution SQL"}

    # ✅ MAINTENANT on peut accéder à data en toute sécurité
    data = result['data']
    
    # ✅ DEBUG : Afficher résultat SQL (APRÈS initialisation de data)
    print(f"   📊 SQL exécuté: {sql}")
    print(f"   📊 Résultat: {len(data)} lignes")
    if len(data) > 0:
        print(f"   📊 Colonnes disponibles: {list(data.columns)}")
        print(f"   📊 Premières lignes:\n{data.head(3)}")

    # Log SQL execution
    tracer.log_sql_query(
        sql=sql,
        result_rows=len(data),
        duration_ms=duration_ms,
        success=True
    )

    if data.empty:
        tracer.log_business_error(
            error_type='empty_result',
            description="Graphique demandé mais aucune donnée disponible",
            sql=sql
        )
        return {"success": False, "error": "Aucune donnée pour le graphique"}
    
    tracer.log_chart_generation(
        chart_type=chart_type,
        data_points=len(data),
        duration_ms=0
    )
    
    # ✅ EXTRAIRE LES PAGES CITÉES
    pages_cited = set()

    if 'source_page' in data.columns:
        for page in data['source_page'].dropna().unique():
            try:
                pages_cited.add(int(page))
            except (ValueError, TypeError):
                print(f"   ⚠️  Impossible de convertir page: {page}")

    if 'pages_sources' in data.columns:
        for pages_str in data['pages_sources'].dropna():
            try:
                pages = [int(p.strip()) for p in str(pages_str).split(',') if p.strip().isdigit()]
                pages_cited.update(pages)
            except (ValueError, TypeError, AttributeError) as e:
                print(f"   ⚠️  Erreur extraction pages_sources: {e}")

    pages_cited = sorted(list(pages_cited))
    print(f"   📄 Pages citées extraites: {pages_cited}")

    # ✅ AJOUTER CITATION À LA RÉPONSE
    response_text = f"📊 Graphique généré avec {len(data)} entrées"

    if pages_cited:
        pages_str = ', '.join(map(str, pages_cited[:15]))
        if len(pages_cited) > 15:
            pages_str += f" (et {len(pages_cited) - 15} autres)"
        response_text += f"\n\n📄 **Sources PDF :** Pages {pages_str}"

    return {
        "success": True,
        "response": response_text,
        "data": data,
        "sql": sql,
        "chart_type": chart_type,
        "intent": "chart",
        "pages_cited": pages_cited
    }


def handle_disambiguation_choice(choice_input: str):
    """Gère le choix de l'utilisateur pour la disambiguation"""
    
    if not st.session_state.awaiting_disambiguation:
        return {"success": False, "error": "Aucune disambiguation en attente"}
    
    disambiguation_info = st.session_state.disambiguation_info
    original_question = st.session_state.original_question
    
    selected_match = st.session_state.disambiguator.resolve_choice(
        choice_input, 
        disambiguation_info
    )
    
    if selected_match is None:
        return {
            "success": False,
            "error": "❌ **Choix invalide**\n\nVeuillez répondre avec un numéro (1, 2, 3...) correspondant aux options proposées.",
            "keep_waiting": True
        }
    
    entity_type = disambiguation_info['entity_type']
    
    # Réinitialiser l'état IMMÉDIATEMENT
    st.session_state.awaiting_disambiguation = False
    st.session_state.disambiguation_info = None
    
    # Construire question enrichie
    if entity_type == 'circonscriptions':
        circ_name = selected_match.get('circonscription_name', '')
        circ_num = selected_match.get('circonscription_num', '')
        region = selected_match.get('region_normalise', '')
        
        enriched_question = f"{original_question} [Circonscription choisie: {circ_name}]"
        confirmation = f"✅ **Parfait !** Vous avez choisi : **{circ_name}** (Circonscription #{circ_num}, {region})\n\n"
    
    elif entity_type == 'candidats':
        candidat = selected_match.get('candidat_normalise', '')
        parti = selected_match.get('parti_normalise', '')
        
        enriched_question = f"{original_question} [Candidat choisi: {candidat}]"
        confirmation = f"✅ **Parfait !** Vous avez choisi : **{candidat}** ({parti})\n\n"
    
    elif entity_type == 'partis':
        parti = selected_match.get('parti_normalise', '')
        
        enriched_question = f"{original_question} [Parti choisi: {parti}]"
        confirmation = f"✅ **Parfait !** Vous avez choisi : **{parti}**\n\n"
    
    elif entity_type == 'regions':
        region = selected_match.get('region_normalise', '')
        
        enriched_question = f"{original_question} [Région choisie: {region}]"
        confirmation = f"✅ **Parfait !** Vous avez choisi : **{region}**\n\n"
    
    else:
        enriched_question = original_question
        confirmation = "✅ **Choix confirmé !**\n\n"
    
    st.session_state.original_question = enriched_question
    
    return {
        "success": True,
        "confirmation": confirmation,
        "reprocess": True,
        "original_question": enriched_question
    }


def check_disambiguation_needed(question: str, tracer: RequestTracer) -> Dict[str, Any]:
    """Vérifie si la question nécessite une disambiguation"""
    
    # ✅ NOUVEAU : Si la question a déjà été enrichie, ne pas redemander
    if any(marker in question for marker in ['[Candidat choisi:', '[Circonscription choisie:', '[Parti choisi:', '[Région choisie:']):
        print(f"   → Question déjà enrichie, pas de disambiguation")
        return {
            'needs_disambiguation': False,
            'disambiguation_info': None,
            'clarification_message': None
        }
    
    start_time = time.time()
    
    ambiguity = st.session_state.disambiguator.detect_ambiguity(question)
    
    duration_ms = (time.time() - start_time) * 1000
    
    tracer.log_step('disambiguation_check', {
        'is_ambiguous': ambiguity.get('is_ambiguous', False),
        'entity_type': ambiguity.get('entity_type'),
        'matches_found': len(ambiguity.get('matches', []))
    }, duration_ms)
    
    if ambiguity['is_ambiguous'] and ambiguity['clarification_needed']:
        
        clarification_msg = st.session_state.disambiguator.generate_clarification_question(ambiguity)
        
        return {
            'needs_disambiguation': True,
            'disambiguation_info': ambiguity,
            'clarification_message': clarification_msg
        }
    
    return {
        'needs_disambiguation': False,
        'disambiguation_info': None,
        'clarification_message': None
    }


def process_question(question: str):
    """Traite intelligemment tous types de questions AVEC TRAÇABILITÉ + DISAMBIGUATION + CACHE ⚡"""
    
    tracer = st.session_state.tracer_manager.create_tracer(
        question,
        session_id=st.session_state.current_conversation_id
    )
    
    # 1. Classifier l'intention
    start_time = time.time()
    intent_result = st.session_state.intent_classifier.classify(question)
    duration_ms = (time.time() - start_time) * 1000
    tracer.log_step('intent_classification', intent_result, duration_ms)

    intent = intent_result['intent']
    chart_type_from_classifier = intent_result.get('chart_type', None)  # ✅ NOUVEAU

    # ✅ NOUVEAU : Log du type de chart détecté
    if chart_type_from_classifier:
        print(f"📊 Type de graphique détecté : {chart_type_from_classifier}")
    
    # ✅ LAYER 0 : Cache exact match (seulement pour sql_query et fraud_analysis)
    if intent in ['sql_query', 'fraud_analysis']:
        print(f"🔍 Vérification cache exact pour: {question[:50]}...")
    cached_response = st.session_state.cache_manager.get_cached_question_response(question)
    
    if cached_response:
        print(f"✅ CACHE HIT EXACT! Réponse instantanée")
        tracer.log_step('cache_exact_hit', {
            'cache_type': 'exact_match',
            'data_rows': len(cached_response.get('data', [])) if cached_response.get('data') else 0
        }, 0)
        
        tracer.save_to_file()
        
        # Retourner réponse cachée directement
        return {
            "success": True,
            "response": cached_response['response'],  # ✅ SANS préfixe
            "data": pd.DataFrame(cached_response['data']) if cached_response.get('data') else None,
            "sql": cached_response.get('sql'),
            "intent": cached_response.get('intent', 'cached'),
            "cached": True,
            "cache_type": 'exact_match'
        }
    
    # ✅ LAYER 1 : Similarité sémantique DÉSACTIVÉE (trop de faux positifs)
    # Le cache exact match suffit amplement
    print(f"⚠️  Cache similarité désactivé (exact match uniquement)")
    
    try:
        # PHASE 0 : VÉRIFIER SI ON ATTEND UNE RÉPONSE DE DISAMBIGUATION
        if st.session_state.awaiting_disambiguation:
            result = handle_disambiguation_choice(question)
            
            if not result['success']:
                if result.get('keep_waiting'):
                    return {
                        "success": True,
                        "response": result['error'],
                        "intent": "disambiguation_retry"
                    }
                else:
                    return result
            
            confirmation_result = {
                "success": True,
                "response": result['confirmation'],
                "intent": "disambiguation_confirmed"
            }
            
            if result.get('reprocess'):
                st.session_state.original_question = result['original_question']
                st.session_state.should_reprocess = True
            
            return confirmation_result
        
        # PHASE 1 : Intent déjà classifié au début (pas besoin de re-classifier)
        tracer.log_intent_classification(
            intent=intent,
            confidence=intent_result.get('confidence', 0.0),
            duration_ms=0  # Déjà fait
        )
        
        # PHASE 2 : VÉRIFIER DISAMBIGUATION
        if intent in ['sql_query', 'chart', 'fraud_analysis']:
            
            disambiguation_check = check_disambiguation_needed(question, tracer)
            
            if disambiguation_check['needs_disambiguation']:
                
                st.session_state.awaiting_disambiguation = True
                st.session_state.disambiguation_info = disambiguation_check['disambiguation_info']
                st.session_state.original_question = question
                
                return {
                    "success": True,
                    "response": disambiguation_check['clarification_message'],
                    "intent": "disambiguation_request"
                }
        
        # PHASE 3 : ROUTER SELON L'INTENT
        if intent == 'conversation':
            response_text = handle_conversation(question)
            result = {
                "success": True,
                "response": response_text,
                "intent": "conversation"
            }
        
        elif intent == 'off_topic':
            response_text = handle_off_topic(question)
            result = {
                "success": True,
                "response": response_text,
                "intent": "off_topic"
            }
        
        elif intent == 'fraud_analysis':
            result = _handle_fraud_analysis_traced(question, tracer)
        
                # Chart request
        elif intent == 'chart':
            result = _handle_sql_query_traced(question, tracer)
            
            if result['success']:
                result['intent'] = 'chart'
                result['chart_type'] = chart_type_from_classifier or 'bar'  # ✅ FIX ICI
                
                # ✅ NOUVEAU : Log du type utilisé
                print(f"📊 Type de chart final : {result['chart_type']}")
                
        else:  # sql_query
            result = _handle_sql_query_traced(question, tracer)

# ✅ NOUVEAU : Cacher la réponse AVANT le return
        if result.get('success') and not result.get('cached'):
            if result.get('intent') not in ['disambiguation_request', 'disambiguation_retry', 'disambiguation_confirmed']:
                try:
                    data_cache = result.get('data')
                    if data_cache is not None and hasattr(data_cache, 'to_dict'):
                        data_cache = data_cache.to_dict('records')

                    st.session_state.cache_manager.cache_question_response(
                        question=question,
                        response=result.get('response', ''),
                        data=data_cache,
                        sql=result.get('sql'),
                        intent=result.get('intent'),
                        metadata={
                            'row_count': result.get('row_count', 0),
                            'chart_type': result.get('chart_type'),
                            'pages_cited': result.get('pages_cited', [])
                        }
                    )
                except Exception as cache_error:
                    print(f"⚠️ Impossible de cacher: {cache_error}")
        
        return result
            
    except Exception as e:
        tracer.log_error('process_question', str(e), type(e).__name__)
        return {"success": False, "error": f"Erreur : {str(e)}"}
        
    finally:
            tracer.save_to_file()


def render_sidebar():
    """Sidebar moderne avec gestion conversations + métriques"""
    
    with st.sidebar:
        st.markdown("### 💬 Conversations")
        
        # ✅ FIX : Reset complet lors nouvelle conversation
        if st.button("➕ **Nouvelle conversation**", use_container_width=True, type="primary"):
            new_conv_id = st.session_state.conversation_manager.create_conversation()
            st.session_state.current_conversation_id = new_conv_id
            st.session_state.messages = []
            
            # ✅ RESET COMPLET
            reset_conversation_state()
            
            st.rerun()
        
        st.markdown("---")
        
        conversations = st.session_state.conversation_manager.get_conversations()
        
        if not conversations:
            st.info("Aucune conversation")
        else:
            for conv in conversations:
                conv_id = conv["id"]
                is_active = conv_id == st.session_state.current_conversation_id
                
                col1, col2 = st.columns([5, 1])
                
                with col1:
                    title = conv['title'][:30] + "..." if len(conv['title']) > 30 else conv['title']
                    button_type = "primary" if is_active else "secondary"
                    
                    if st.button(
                        f"{'📌' if is_active else '💬'} {title}",
                        key=f"conv_{conv_id}",
                        use_container_width=True,
                        type=button_type
                    ):
                        if conv_id != st.session_state.current_conversation_id:
                            st.session_state.current_conversation_id = conv_id
                            st.session_state.messages = st.session_state.conversation_manager.load_messages(conv_id)
                            
                            # ✅ RESET COMPLET
                            reset_conversation_state()
                            
                            st.rerun()
                
                with col2:
                    if st.button("🗑️", key=f"del_{conv_id}"):
                        st.session_state.conversation_manager.delete_conversation(conv_id)
                        
                        if conv_id == st.session_state.current_conversation_id:
                            new_conv_id = st.session_state.conversation_manager.create_conversation()
                            st.session_state.current_conversation_id = new_conv_id
                            st.session_state.messages = []
                            
                            # ✅ RESET COMPLET
                            reset_conversation_state()
                        
                        st.rerun()
        
        st.markdown("---")
        
        # ✅ FIX : Reset lors du passage aux métriques
        if st.button("📊 **Voir les métriques**", use_container_width=True):
            st.session_state.show_metrics = not st.session_state.get('show_metrics', False)
            
            # ✅ RESET COMPLET lors du changement de page
            reset_conversation_state()
            
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 🇨🇮 Élections 2025")
        st.caption("Données officielles CEI")
        st.caption("Powered by Christ-Emmanuel")


def render_metrics_dashboard():
    """Affiche le dashboard de métriques"""
    
    st.title("📊 Tableau de bord des métriques")
    
    metrics = st.session_state.tracer_manager.get_metrics_summary()
    
    if not metrics:
        st.info("📭 Aucune métrique disponible pour le moment. Posez quelques questions pour générer des données !")
        return
    
    # ========================================================================
    # SECTION 1 : MÉTRIQUES PRINCIPALES
    # ========================================================================
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "🔢 Requêtes totales",
            f"{metrics['total_requests']}"
        )
    
    with col2:
        success_rate = metrics['success_rate']
        st.metric(
            "✅ Taux de succès",
            f"{success_rate:.1f}%",
            delta=f"{success_rate - 100:.1f}%" if success_rate < 100 else None,
            delta_color="normal"
        )
    
    with col3:
        st.metric(
            "⏱️ Durée moyenne",
            f"{metrics['avg_duration_ms']:.0f}ms"
        )
    
    with col4:
        st.metric(
            "🤖 Tokens totaux",
            f"{metrics['total_llm_tokens']:,}"
        )
    
    st.markdown("---")
    
    # ========================================================================
    # SECTION 2 : RAPPORT + ACTIONS PRINCIPALES
    # ========================================================================
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📈 Rapport de performance")
        report = st.session_state.tracer_manager.get_performance_report()
        st.text(report)
    
    with col2:
        st.subheader("🎯 Actions")
        
        # Bouton Exporter CSV
        if st.button("📥 Exporter en CSV", use_container_width=True):
            csv_file = st.session_state.tracer_manager.export_metrics_csv()
            if csv_file:
                st.success(f"✅ Exporté : {csv_file.name}")
                
                try:
                    with open(csv_file, 'rb') as f:
                        st.download_button(
                            label="⬇️ Télécharger le CSV",
                            data=f,
                            file_name=csv_file.name,
                            mime="text/csv",
                            use_container_width=True
                        )
                except Exception as e:
                    st.error(f"Erreur lecture : {e}")
        
        # Bouton Retour au chat
        if st.button("💬 Retour au chat", use_container_width=True, type="primary"):
            st.session_state.show_metrics = False
            reset_conversation_state()
            st.rerun()
    
    st.markdown("---")
    
    # ========================================================================
    # SECTION 3 : GESTION DU CACHE
    # ========================================================================
    st.subheader("🗑️ Gestion du cache")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 **Vider cache complet**", use_container_width=True):
            try:
                cleared = {"embeddings": 0, "sql": 0, "questions": 0}
                
                # Vider cache questions
                if hasattr(st.session_state, 'cache_manager'):
                    cleared['questions'] = st.session_state.cache_manager.clear_questions_cache()
                    cleared['embeddings'] = st.session_state.cache_manager.clear_embeddings_cache()
                    cleared['sql'] = st.session_state.cache_manager.clear_sql_cache()
                
                # Vider cache RAG
                if hasattr(st.session_state, 'sql_generator') and st.session_state.sql_generator.rag_enabled:
                    if hasattr(st.session_state.sql_generator.rag, 'clear_cache'):
                        st.session_state.sql_generator.rag.clear_cache()
                
                st.success(f"✅ Cache vidé : {cleared['questions']} questions, {cleared['embeddings']} embeddings, {cleared['sql']} SQL")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"❌ Erreur : {e}")
    
    with col2:
        if st.button("🗑️ Questions uniquement", use_container_width=True):
            try:
                if hasattr(st.session_state, 'cache_manager'):
                    count = st.session_state.cache_manager.clear_questions_cache()
                    st.success(f"✅ {count} questions supprimées")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Erreur : {e}")
    
    with col3:
        # Stats cache
        if hasattr(st.session_state, 'cache_manager'):
            stats = st.session_state.cache_manager.get_cache_stats()
            st.info(f"📊 Cache actuel:\n- {stats['questions_count']} questions\n- {stats['embeddings_count']} embeddings\n- {stats['sql_count']} SQL")
        else:
            st.caption("Stats cache non disponibles")
    
    st.markdown("---")
    
    # ========================================================================
    # SECTION 4 : TRACES RÉCENTES
    # ========================================================================
    st.subheader("🔍 Traces récentes")
    
    traces = st.session_state.tracer_manager.get_traces(limit=20)
    
    if traces:
        data = []
        for t in traces:
            data.append({
                'Question': t['question'][:50] + "..." if len(t['question']) > 50 else t['question'],
                'Succès': "✅" if t['success'] else "❌",
                'Durée (ms)': f"{t['metrics']['total_duration_ms']:.0f}",
                'LLM Calls': t['metrics']['llm_calls'],
                'Tokens': t['metrics']['llm_tokens_input'] + t['metrics']['llm_tokens_output'],
                'Timestamp': t['start_time'][:19]
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune trace récente")


# MAIN APP
init_session_state()

if not st.session_state.app_ready:
    st.error(f"⚠️ {st.session_state.get('error_message', 'Erreur')}")
    st.stop()

render_sidebar()

# AFFICHAGE CONDITIONNEL : Chat ou Métriques
if st.session_state.get('show_metrics', False):
    render_metrics_dashboard()

else:
    # Mode chat
    st.markdown("""
    <div class="custom-header">
        <h1>🗳️ Élections Législatives 2025</h1>
        <p>Assistant IA Intelligent • Résultats, Analyses & Détection d'Anomalies</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Charger messages
    if not st.session_state.messages:
        st.session_state.messages = st.session_state.conversation_manager.load_messages(
            st.session_state.current_conversation_id
        )
    
    # Afficher historique
    for idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Graphique
            if message["role"] == "assistant" and "chart_type" in message:
                try:
                    data = pd.DataFrame(message["data_preview"])
                    chart = create_chart(
                        data, 
                        message["chart_type"],
                        st.session_state.messages[idx-1]["content"] if idx > 0 else ""
                    )
                    if chart:
                        st.plotly_chart(chart, use_container_width=True)
                except:
                    pass
            
            # Tableau avec CSV
            if message["role"] == "assistant" and message.get("show_table") and "data_preview" in message:
                try:
                    data = pd.DataFrame(message["data_preview"])
                    st.dataframe(data, use_container_width=True, hide_index=True)
                    
                    csv = data.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label=f"📥 **Télécharger** ({len(data)} résultats CSV)",
                        data=csv,
                        file_name=f"resultats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        key=f"csv_{idx}"
                    )
                except:
                    pass
            
            # SQL
            if message["role"] == "assistant" and message.get("sql"):
                with st.expander("🔍 **Voir la requête SQL**"):
                    st.code(message["sql"], language="sql")
    
# ✅ FIX : Bloquer l'input pendant le traitement + Message clair
    if st.session_state.processing:
        st.chat_input(
            "⏳ Traitement en cours, veuillez patienter...",
            disabled=True,
            key="blocked_input"
        )
        user_input = None
    else:
        user_input = st.chat_input(
            "💬 Posez votre question (résultats, fraudes, anomalies...)",
            disabled=False
        )

    # ✅ FIX : Gérer reprocess AVANT de traiter user_input
    if st.session_state.get('should_reprocess', False) and not user_input:
        st.session_state.should_reprocess = False
        user_input = st.session_state.original_question
        st.session_state.original_question = None

    if user_input:
        # ✅ BLOQUER IMMÉDIATEMENT
        st.session_state.processing = True
        
        # Ajouter message user
        user_message = {"role": "user", "content": user_input}
        
        st.session_state.messages.append(user_message)
        st.session_state.conversation_manager.add_message(
            st.session_state.current_conversation_id,
            user_message
        )
        
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # ✅ UTILISER TRY/FINALLY pour garantir le déblocage
        try:
            with st.chat_message("assistant"):
                with st.spinner("🤔 Analyse en cours..."):
                    result = process_question(user_input)
                    
                    if not result['success']:
                        response_text = f"❌ **Erreur**\n\n{result['error']}"
                        st.error(response_text)
                        assistant_message = {"role": "assistant", "content": response_text}
                    
                    else:
                        intent = result.get('intent', 'unknown')
                        
                        # CAS SPÉCIAL : DISAMBIGUATION
                        if intent == 'disambiguation_request':
                            st.markdown(result['response'])
                            
                            assistant_message = {
                                "role": "assistant",
                                "content": result['response'],
                                "intent": "disambiguation"
                            }
                        
                        elif intent == 'disambiguation_confirmed':
                            st.success(result['response'])
                            
                            assistant_message = {
                                "role": "assistant",
                                "content": result['response'],
                                "intent": "disambiguation_confirmed"
                            }
                            
                            if result.get('reprocess'):
                                st.session_state.should_reprocess = True
                        
                        elif intent == 'disambiguation_retry':
                            st.warning(result['response'])
                            
                            assistant_message = {
                                "role": "assistant",
                                "content": result['response'],
                                "intent": "disambiguation_retry"
                            }
                        
                        # CAS NORMAUX
                        else:
                            st.markdown(result['response'])
                            
                            assistant_message = {
                                "role": "assistant",
                                "content": result['response'],
                                "intent": intent
                            }
                            
                            if 'pages_cited' in result and result['pages_cited']:
                                assistant_message['pages_cited'] = result['pages_cited']
                            
                            # Graphiques
                            if intent == 'chart':
                                # ✅ FIX : Utiliser chart_type depuis result (qui vient du classifier)
                                chart_type_final = result.get('chart_type', 'bar')
                                
                                # ✅ NOUVEAU : Validation du type
                                if chart_type_final not in ['pie', 'bar', 'line']:
                                    print(f"⚠️  Type invalide '{chart_type_final}', utilisation de 'bar'")
                                    chart_type_final = 'bar'
                                
                                chart = create_chart(
                                    result['data'],
                                    chart_type_final,  # ✅ FIX ICI
                                    user_input
                                )
                                
                                if chart:
                                    st.plotly_chart(
                                        chart, 
                                        use_container_width=True,
                                        key=f"chart_{len(st.session_state.messages)}"
                                    )
                                    assistant_message["chart_type"] = chart_type_final  # ✅ FIX ICI
                                    assistant_message["data_preview"] = result['data'].head(30).to_dict()
                                
                                with st.expander("🔍 **Voir la requête SQL**"):
                                    st.code(result['sql'], language="sql")
                                
                                assistant_message["sql"] = result.get('sql')
                            
                            # SQL query
                            elif intent == 'sql_query':
                                assistant_message["sql"] = result.get('sql')
                                
                                # Graphique
                                if result.get('chart_request', {}).get('requested') and result.get('data') is not None and not result['data'].empty:
                                    # ✅ FIX : Utiliser chart_type du classifier si disponible
                                    chart_type_final = chart_type_from_classifier or result['chart_request'].get('type', 'bar')
                                    
                                    # ✅ NOUVEAU : Validation
                                    if chart_type_final not in ['pie', 'bar', 'line']:
                                        chart_type_final = 'bar'
                                    
                                    chart = create_chart(
                                        result['data'],
                                        chart_type_final,  # ✅ FIX ICI
                                        user_input
                                    )
                                    
                                    if chart:
                                        # ✅ AJOUT : key unique
                                        st.plotly_chart(
                                            chart, 
                                            use_container_width=True,
                                            key=f"chart_sql_{len(st.session_state.messages)}"  # ✅ FIX ICI
                                        )
                                        assistant_message["chart_type"] = result['chart_request']['type']
                                        assistant_message["data_preview"] = result['data'].head(30).to_dict()
                                
                                # Tableau
                                elif (not result.get('chart_request', {}).get('requested') 
                                    and result.get('data') is not None 
                                    and len(result['data']) > 1):
                                    
                                    preview_size = min(20, len(result['data']))
                                    data_preview = result['data'].head(preview_size).copy()
                                    
                                    if 'source_page' in data_preview.columns:
                                        data_preview['📄 Page'] = data_preview['source_page'].apply(
                                            lambda x: f"p.{int(x)}" if pd.notna(x) else ""
                                        )
                                        
                                        cols_to_hide = ['source_page', 'table_id', 'row_id']
                                        cols = [c for c in data_preview.columns if c not in cols_to_hide]
                                        
                                        if '📄 Page' in cols:
                                            cols.remove('📄 Page')
                                            cols.append('📄 Page')
                                        
                                        data_preview = data_preview[cols]
                                    
                                    st.dataframe(data_preview, use_container_width=True, hide_index=True)
                                    
                                    if len(result['data']) > preview_size:
                                        st.caption(f"*{preview_size} premiers résultats sur {len(result['data'])}*")
                                    
                                    csv = result['data'].to_csv(index=False, encoding='utf-8-sig')
                                    st.download_button(
                                        label=f"📥 **Télécharger les {len(result['data'])} résultats** (CSV)",
                                        data=csv,
                                        file_name=f"resultats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                        mime="text/csv"
                                    )
                                    
                                    assistant_message["show_table"] = True
                                    assistant_message["data_preview"] = result['data'].to_dict()
                                
                                # SQL expander
                                with st.expander("🔍 **Voir la requête SQL**"):
                                    st.code(result['sql'], language="sql")
                            
                            # Fraud analysis
                            elif intent == 'fraud_analysis' and result.get('data') is not None:
                                data = result['data']
                                if not data.empty:
                                    st.dataframe(data.head(20), use_container_width=True, hide_index=True)
                                    
                                    csv = data.to_csv(index=False, encoding='utf-8-sig')
                                    st.download_button(
                                        label=f"📥 **Télécharger le rapport** ({len(data)} anomalies)",
                                        data=csv,
                                        file_name=f"anomalies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                        mime="text/csv"
                                    )
                                    
                                    assistant_message["show_table"] = True
                                    assistant_message["data_preview"] = data.to_dict()
                    
                    # Sauvegarder message assistant
                    st.session_state.messages.append(assistant_message)
                    st.session_state.conversation_manager.add_message(
                        st.session_state.current_conversation_id,
                        assistant_message
                    )
        
        finally:
            # ✅ TOUJOURS débloquer, même en cas d'erreur
            st.session_state.processing = False
        
        st.rerun()