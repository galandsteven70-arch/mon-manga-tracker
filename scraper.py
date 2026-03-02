import os
import json
import re
import requests
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, firestore

# 1. Connexion à Firebase
if not firebase_admin._apps:
    service_account_info = json.loads(os.environ.get('FIREBASE_SERVICE_ACCOUNT'))
    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- CONFIGURATION ANTI-BLOCAGE ---
# On change radicalement les headers pour imiter un téléphone Android
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Upgrade-Insecure-Requests': '1'
}

def run_scraper():
    mangas_ref = db.collection('mangas')
    mangas = mangas_ref.stream()

    for m in mangas:
        m_data = m.to_dict()
        m_id = m.id
        nom_manga = m_data.get('titre')
        url_fiche = m_data.get('url_manga')
        
        try:
            dernier_connu = float(m_data.get('dernier_chapitre', 0))
        except:
            dernier_connu = 0.0

        if not url_fiche:
            continue

        print(f"🔍 Tentative d'accès furtif pour : {nom_manga}")
        try:
            # Utilisation d'une session pour gérer les cookies automatiquement
            session = requests.Session()
            response = session.get(url_fiche, headers=HEADERS, timeout=30)
            html_content = response.text
            
            # On cherche "Ch. 299" ou "Ch.299"
            pattern = r"Ch\.\s*(\d+(?:\.\d+)?)"
            trouvailles = re.findall(pattern, html_content, re.IGNORECASE)
            
            if trouvailles:
                liste_chapitres = [float(x) for x in trouvailles]
                nouveau_chap = max(liste_chapitres)
                
                print(f"📈 Succès ! Trouvé : {nouveau_chap}")

                if nouveau_chap > dernier_connu:
                    print(f"✨ MAJ : {dernier_connu} -> {nouveau_chap}")
                    
                    # On met à jour sans chercher le lien pour l'instant (plus sûr)
                    mangas_ref.document(m_id).update({
                        'dernier_chapitre': nouveau_chap,
                        'lien_chapitre': url_fiche # On renvoie vers la fiche par défaut
                    })
                else:
                    print(f"✅ Déjà à jour.")
            else:
                print(f"❌ Blocage persistant (Taille : {len(html_content)}).")
                # DEBUG : Affiche les 500 premiers caractères pour voir l'erreur du site
                print(f"Contenu reçu (début) : {html_content[:500]}")

        except Exception as e:
            print(f"🔥 Erreur : {e}")

if __name__ == "__main__":
    run_scraper()
