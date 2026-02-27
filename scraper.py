# Futur scraper
import os
import json
import requests
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, firestore

# 1. Connexion à Firebase via le Secret GitHub
if not firebase_admin._apps:
    service_account_info = json.loads(os.environ.get('FIREBASE_SERVICE_ACCOUNT'))
    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 2. Configuration du robot pour Scan-Manga
URL_BASE = "https://m.scan-manga.com/derniers-chapitres-ajoutes.html"
HEADERS = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1'}

def run_scraper():
    # On récupère ta liste de mangas dans Firebase
    mangas_ref = db.collection('mangas')
    mangas = mangas_ref.stream()

    # On télécharge la page des sorties
    response = requests.get(URL_BASE, headers=HEADERS)
    soup = BeautifulSoup(response.text, 'html.parser')

    for m in mangas:
        m_data = m.to_dict()
        m_id = m.id
        nom_manga = m_data.get('titre')
        dernier_connu = m_data.get('dernier_chapitre')

        # On cherche le manga sur la page (Logique simplifiée pour Scan-Manga)
        # On cherche le lien qui contient le nom du manga
        link_tag = soup.find('a', string=lambda t: t and nom_manga.lower() in t.lower())
        
        if link_tag:
            # On cherche le numéro du chapitre dans le texte voisin
            parent = link_tag.find_parent('div')
            chapitre_text = parent.find('span', class_='chapitre').text # À ajuster selon le site précis
            # Extraction du nombre (ex: "Chapitre 1110" -> 1110)
            nouveau_chap = float(''.join(filter(lambda x: x.isdigit() or x == '.', chapitre_text)))

            if nouveau_chap > dernier_connu:
                print(f"NOUVEAU ! {nom_manga} : {nouveau_chap}")
                # Mise à jour Firebase
                mangas_ref.document(m_id).update({
                    'dernier_chapitre': nouveau_chap,
                    'lien_chapitre': "https://m.scan-manga.com" + link_tag['href']
                })

if __name__ == "__main__":
    run_scraper()
