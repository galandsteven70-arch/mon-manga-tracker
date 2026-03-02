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

# Configuration Navigation (Simule un vrai navigateur)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def run_scraper():
    mangas_ref = db.collection('mangas')
    mangas = mangas_ref.stream()

    for m in mangas:
        m_data = m.to_dict()
        m_id = m.id
        nom_manga = m_data.get('titre')
        url_fiche = m_data.get('url_manga')
        dernier_connu = m_data.get('dernier_chapitre', 0)

        if not url_fiche:
            print(f"⚠️ Pas d'URL fiche pour {nom_manga}")
            continue

        print(f"🔍 Vérification de : {nom_manga}...")
        try:
            response = requests.get(url_fiche, headers=HEADERS)
            soup = BeautifulSoup(response.text, 'html.parser')

            nouveau_chap = 0
            lien_final = url_fiche

            # --- DÉTECTION AGRESSIVE DES CHAPITRES ---
            for a in soup.find_all('a'):
                texte = a.get_text().strip()
                href = a.get('href', '')
                
                # On cherche des indices de chapitre dans le texte ou l'URL
                if any(x in texte.lower() for x in ["chapitre", "ch.", "chap"]) or "/chapitre-" in href.lower():
                    try:
                        # On extrait les nombres du texte (ex: "Chapitre 299.5" -> 299.5)
                        nombres = re.findall(r"(\d+\.?\d*)", texte)
                        
                        if nombres:
                            num_found = float(nombres[0])
                            
                            # On garde le premier (le plus récent en haut de page)
                            if nouveau_chap == 0:
                                nouveau_chap = num_found
                                # Nettoyage de l'URL
                                if href.startswith('http'):
                                    lien_final = href
                                else:
                                    lien_final = "https://m.scan-manga.com" + href
                                break 
                    except:
                        continue

            # --- COMPARAISON ET MISE À JOUR ---
            if nouveau_chap > 0:
                if nouveau_chap > dernier_connu:
                    print(f"✨ MAJ TROUVÉE : {nom_manga} (Chapitre {nouveau_chap})")
                    mangas_ref.document(m_id).update({
                        'dernier_chapitre': nouveau_chap,
                        'lien_chapitre': lien_final
                    })
                else:
                    print(f"✅ {nom_manga} est déjà à jour (Site: {nouveau_chap} / Firebase: {dernier_connu})")
            else:
                print(f"❌ Aucun numéro de chapitre détecté sur la page de {nom_manga}.")

        except Exception as e:
            print(f"🔥 Erreur sur {nom_manga}: {e}")

if __name__ == "__main__":
    run_scraper()
