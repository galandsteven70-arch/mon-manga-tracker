# Futur scraper
import os
import json
import requests
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, firestore

# 1. Connexion sécurisée à Firebase
if not firebase_admin._apps:
    # Récupération de la clé secrète que tu as enregistrée dans GitHub Settings
    service_account_info = json.loads(os.environ.get('FIREBASE_SERVICE_ACCOUNT'))
    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 2. Configuration pour Scan-Manga
URL_BASE = "https://m.scan-manga.com/derniers-chapitres-ajoutes.html"
HEADERS = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'}

def run_scraper():
    # On récupère tes mangas dans Firebase
    mangas_ref = db.collection('mangas')
    mangas = mangas_ref.stream()

    # On va lire les dernières sorties sur le site
    print("Vérification des sorties sur Scan-Manga...")
    response = requests.get(URL_BASE, headers=HEADERS)
    soup = BeautifulSoup(response.text, 'html.parser')

    for m in mangas:
        m_data = m.to_dict()
        m_id = m.id
        nom_manga = m_data.get('titre')
        dernier_connu = m_data.get('dernier_chapitre', 0)

        # On cherche le nom du manga dans les liens de la page
        link_tag = soup.find('a', string=lambda t: t and nom_manga.lower() in t.lower())
        
        if link_tag:
            # On remonte au bloc parent pour trouver le numéro du chapitre
            parent = link_tag.find_parent('div')
            chapitre_span = parent.find('span', class_='chapitre') if parent else None
            
            if chapitre_span:
                # On extrait juste le numéro (ex: "1120")
                nouveau_txt = ''.join(filter(lambda x: x.isdigit() or x == '.', chapitre_span.text))
                nouveau_chap = float(nouveau_txt) if nouveau_txt else 0

                # Si le numéro est plus grand que celui en base de données -> MAJ !
                if nouveau_chap > dernier_connu:
                    print(f"Update trouvé pour {nom_manga} : Chapitre {nouveau_chap}")
                    mangas_ref.document(m_id).update({
                        'dernier_chapitre': nouveau_chap,
                        'lien_chapitre': "https://m.scan-manga.com" + link_tag['href']
                    })
                else:
                    print(f"Pas de nouveau chapitre pour {nom_manga}.")

if __name__ == "__main__":
    run_scraper()
