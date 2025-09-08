from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import os
from typing import Dict, List, Any
import logging

load_dotenv()


# Default configurations
DEFAULT_AGENT_INSTRUCTION = """You are a helpful AI assistant.
Speak in a professional and friendly manner.
Be concise and clear in your responses.
Use the available tools when needed to assist users effectively."""

DEFAULT_BEGIN_MESSAGE = "Hello! I'm your AI assistant. How can I help you today?"

DEFAULT_SESSION_INSTRUCTION = """# Task
Provide assistance by using the tools that you have access to when needed.
Begin the conversation by saying: "{begin_message}"
"""

DEFAULT_SEARCH_WEB_TOOL = {
    'id': 'search_web',
    'name': 'search_web',
    'description': 'Search the web using DuckDuckGo',
    'requestType': 'GET',
    'requestUrl': 'https://api.duckduckgo.com/',
    'parameters': [
        {
            'name': 'query',
            'type': 'string',
            'required': True,
            'description': 'The search query',
            'defaultValue': ''
        }
    ],
    'enabled': True
}

DEFAULT_END_CALL_TOOL = {
    'id': 'end_call',
    'name': 'end_call',
    'description': 'End the current call/session when conversation is complete',
    'requestType': 'BUILTIN',
    'requestUrl': '',
    'parameters': [
        {
            'name': 'reason',
            'type': 'string',
            'required': False,
            'description': 'Reason for ending the call',
            'defaultValue': 'Call completed'
        }
    ],
    'enabled': True
}

class ConfigurationLoader:
    def __init__(self):
        """Initialize Firebase connection using environment variables"""
        try:
            if not firebase_admin._apps:
                # Create credentials from environment variables
                firebase_config = {
                    "type": "service_account",
                    "project_id": "calldash-51b0f",
                    "private_key_id": "4c0198d1e8df878e983b83ca233f2e502820071a",
                    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDaa7IkYHLWZNUL\nCDa3Hs+6JDr92KDIVYEEslHRbI9aOMoqs6HSJiGkXPyHSr9RdiQ6vGc8JEdBruhH\nUszJZT6oVcLVC1cu1AXJWQKE7Grglyhp6kJbfDyYOvJv5Z/lMOQTmlRJzomjPXld\n0whsZHLxLM86DRWMAmg95xqHm/LYUGH3y8++Nlg9kMZs5Ld2ANqxbKRSemvEMhm9\nOJpRUTLhbB8QmL9/h6pqARtL86VJ+Z3FU/1c6nwjS10U939r2iHOXBWP7QWEmM6q\nX1St9EgdM2vcKj2J5XN1nF8tsepKuM1HqGvLBw4iDT+QvhQpzy8CalbrGIBoHH6q\nX1MVWudHAgMBAAECggEARcItpAaVxrlvfVWDPBsAFyApIxfDyhfc2+Yj0XINmrAW\niWrTnO2GwxrboE4UKm1EBupTQlcH1weIsfbU5uGKEHNLhYVYs+ENdBAUiOWFAPPl\n+WXTCar1I114Ppqk5asmvMgGcYggV11z3K5gu1WdjD9Wc+Dn586BAnxD8dmxxrnW\nARJYHhDPYAajEb7xIO34cOKGpUqPrtEUCzeb1+yE5aGawn57ZnuWvbLnwmquoEwJ\n8/Pe4g9Pl5eYSk16BuKzIlooTWcQbZjNG+OrPoZtamO+0Mnr1LzIqIqV+As7UMjT\nOZdtDx6TJH3QplFyi++htYtbwaDYdGE3BczfYdMe+QKBgQD/d1JJ5fHyj0y8NchR\nLrBmFE54VSrUklOLWIhhsN+eQd3BcDMui2nPSAg4OnTpz/NCQ2vbT/xg4BwF2K1S\n2gPPdCtSnMSXsVvQClDvClYemMVRv2H2tQvzg7gZdpRkbn4DmCJ4ov1cUufp5trb\nN4Zx34tJGh4DE3eUHM3wC/Y0uwKBgQDa4I31PJV+SnOBhU0qKpuSXEiUzvqG01dr\n3M9Y9UVn1S5ytgSBRjigTLkDSs1yxyGLDFLGL9WDz7NiamPUeuIyiir0yG6GZpQI\nGHUlKz9mVJTujXEy8tToj99GpjwL1bJd7avn5cOu3FsARHtiwiRegWOYD0YsAZb+\nKJfE35t05QKBgGA+IcA5YudQ2UXmtSrwfgBXEiD/ZP1kixjqJ6c2LWi/w72GeaHF\nX/15U69rRnR3pVuHbvDWt2v/wk7pjJK0E89qIpAjA2Vqqf48hLUpnbw1LdFYWp3J\nI1GAhDEDnXAguFS+Ue5E6VKI4VobYMRJrNrlruHBdyENinVATM1slDrVAoGALCvp\nOjaxzLzltpvaSMo0f0MUesOSl6cLG3+CcOd+zEefihLlsdkkEGWraNitwZ4iTNd9\n1PVOV72Q7CmgX/80qxJrPN8+Pu1wrnmRGqExuEsVi1cMI0YSZaSzYKSntZO43W/b\no38hEKbzzogDhpi7kj72hHeAp9ziRgSXLGocC2kCgYBZ9S9Fj42YmuGGUanSVfWw\nODzkcrtJTJ31gvQwMFyZj4yr0vJ4+rbepEGZJwSbTv/UAb2TXc9RvN//czVOLM3z\nMnPMeGDSyuWgs8iVm4qrwsXjs4BaRNy80mNV8vJfoUqd91HCxl02euFCP7nypA+E\nfUdgcd/JnXQMPlpSP1KNDQ==\n-----END PRIVATE KEY-----\n".replace('\\n', '\n'),
                    "client_email": "firebase-adminsdk-fbsvc@calldash-51b0f.iam.gserviceaccount.com",
                    "client_id": "100032943132406344635",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.getenv('FIREBASE_CLIENT_EMAIL', 'placeholder@placeholder-project.iam.gserviceaccount.com')}",
                    "universe_domain": "googleapis.com"
                }
                
                cred = credentials.Certificate(firebase_config)
                firebase_admin.initialize_app(cred)
            
            self.db = firestore.client()
            logging.info("Firebase initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize Firebase: {e}")
            self.db = None
    
    def load_configuration(self) -> Dict[str, Any]:
        """Load configuration from Firebase or return defaults"""
        config = {
            'agentInstruction': DEFAULT_AGENT_INSTRUCTION,
            'beginMessage': DEFAULT_BEGIN_MESSAGE,
            'tools': [DEFAULT_SEARCH_WEB_TOOL, DEFAULT_END_CALL_TOOL]
        }
        
        if not self.db:
            logging.warning("Firebase not available, using default configuration")
            return config
            
        try:
            doc_ref = self.db.collection('configurations').document('current')
            doc = doc_ref.get()
            
            if doc.exists:
                stored_config = doc.to_dict()
                config.update(stored_config)
                logging.info("Configuration loaded from Firebase")
            else:
                logging.info("No configuration found in Firebase, using defaults")
                
        except Exception as e:
            logging.error(f"Error loading configuration from Firebase: {e}")
            
        return config
    
    def get_session_instruction(self, begin_message: str) -> str:
        """Generate session instruction with dynamic begin message"""
        return DEFAULT_SESSION_INSTRUCTION.format(begin_message=begin_message)
    
    def get_enabled_tools(self, tools: List[Dict]) -> List[Dict]:
        """Filter and return only enabled tools"""
        return [tool for tool in tools if tool.get('enabled', True)]

# Global instance
config_loader = ConfigurationLoader()