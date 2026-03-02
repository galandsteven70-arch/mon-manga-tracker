import os
import json
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

# Configuration Navigation
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

def run_scraper():
    mangas_ref = db.collection('mangas')
    mangas = mangas_ref.stream()

    for m in mangas:
        m_data = m.to_dict()
        m_id = m.id
        nom_manga = m_data.get('titre')
        url_fiche = m_data.get('url_manga') # Le lien direct vers la page du manga
        dernier_connu = m_data.get('dernier_chapitre', 0)

        if not url_fiche:
            print(f"⚠️ Pas d'URL fiche pour {nom_manga}. Ajoute le champ 'url_manga' dans Firebase.")
            continue

        print(f"🔍 Vérification de : {nom_manga}...")
        try:
            response = requests.get(url_fiche, headers=HEADERS)
            soup = BeautifulSoup(response.text, 'html.parser')

            # On cherche les spans avec la classe 'chapitre' (structure Scan-Manga)
            liste_chapitres = soup.find_all('span', class_='chapitre')
            
            if liste_chapitres:
                # On prend le premier de la liste (le plus récent en haut)
                texte_chap = liste_chapitres[0].get_text()
                # On extrait le nombre (ex: "Chapitre 299" -> 299)
                nouveau_txt = ''.join(filter(lambda x: x.isdigit() or x == '.', texte_chap))
                nouveau_chap = float(nouveau_txt) if nouveau_txt else 0

                if nouveau_chap > dernier_connu:
                    print(f"✨ MAJ TROUVÉE : {nom_manga} (Chapitre {nouveau_chap})")
                    
                    # On cherche le lien du chapitre (souvent le parent <a>)
                    parent_link = liste_chapitres[0].find_parent('a')
                    lien_final = "https://m.scan-manga.com" + parent_link['href'] if parent_link else url_fiche
                    
                    mangas_ref.document(m_id).update({
                        'dernier_chapitre': nouveau_chap,
                        'lien_chapitre': lien_final
                    })
                else:
                    print(f"✅ {nom_manga} est déjà à jour (Chapitre {nouveau_chap}).")
            else:
                print(f"❌ Impossible de trouver les chapitres sur la page de {nom_manga}.")
                
        except Exception as e:
            print(f"🔥 Erreur sur {nom_manga}: {e}")

if __name__ == "__main__":
    run_scraper()
