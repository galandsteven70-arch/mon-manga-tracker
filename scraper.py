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

            # Sur ta photo, les chapitres sont dans des liens <a> 
            # On cherche tous les liens qui contiennent "Chapitre"
            nouveau_chap = 0
            lien_final = url_fiche

            for a in soup.find_all('a'):
                texte = a.get_text().strip()
                if "Chapitre" in texte:
                    # On extrait le numéro (ex: "Chapitre 299" -> 299)
                    try:
                        num_str = texte.replace("Chapitre", "").strip().split()[0]
                        num_found = float(num_str)
                        
                        # Le premier qu'on trouve est le plus haut dans la liste (le plus récent)
                        if nouveau_chap == 0:
                            nouveau_chap = num_found
                            # On récupère le lien "Lire en ligne" qui est juste à côté
                            # Ou on prend directement le lien du chapitre
                            lien_final = a['href']
                            if not lien_final.startswith('http'):
                                lien_final = "https://m.scan-manga.com" + lien_final
                            break 
                    except:
                        continue

            if nouveau_chap > dernier_connu:
                print(f"✨ MAJ TROUVÉE : {nom_manga} (Chapitre {nouveau_chap})")
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
