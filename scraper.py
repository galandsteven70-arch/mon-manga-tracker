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

# Configuration Navigation (Simule un vrai navigateur PC)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7'
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

        print(f"🔍 Scan de : {nom_manga}...")
        try:
            response = requests.get(url_fiche, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')

            nouveau_chap = 0
            lien_final = url_fiche

            # --- STRATÉGIE BASÉE SUR TES CAPTURES D'ÉCRAN ---
            # On cherche les <div class="chapitre_nom">
            blocs_chapitres = soup.find_all('div', class_='chapitre_nom')
            
            if not blocs_chapitres:
                # Plan B : Si la classe n'est pas trouvée, on cherche tous les liens
                blocs_chapitres = soup.find_all('a')

            for bloc in blocs_chapitres:
                # Si c'est un div, on cherche le lien <a> à l'intérieur
                lien_a = bloc if bloc.name == 'a' else bloc.find('a')
                
                if lien_a:
                    texte = lien_a.get_text().strip()
                    href = lien_a.get('href', '')

                    # On cherche "Chapitre" ou "Ch." dans le texte
                    if "chapitre" in texte.lower() or "ch." in texte.lower():
                        # Extraction du numéro (ex: "Chapitre 299" -> 299)
                        nombres = re.findall(r"(\d+\.?\d*)", texte)
                        if nombres:
                            num_found = float(nombres[0])
                            
                            # Le premier trouvé est le plus récent
                            if nouveau_chap == 0:
                                nouveau_chap = num_found
                                # Construction de l'URL propre
                                if href.startswith('http'):
                                    lien_final = href
                                elif href.startswith('/'):
                                    lien_final = "https://www.scan-manga.com" + href
                                else:
                                    lien_final = url_fiche
                                break

            # --- MISE À JOUR FIREBASE ---
            if nouveau_chap > 0:
                # Important : Convertir dernier_connu en float au cas où c'est un entier
                if nouveau_chap > float(dernier_connu):
                    print(f"✨ MAJ DÉTECTÉE : {nom_manga} ({dernier_connu} -> {nouveau_chap})")
                    mangas_ref.document(m_id).update({
                        'dernier_chapitre': nouveau_chap,
                        'lien_chapitre': lien_final
                    })
                else:
                    print(f"✅ {nom_manga} est déjà à jour (Trouvé: {nouveau_chap} / Connu: {dernier_connu})")
            else:
                print(f"❌ Impossible d'extraire un numéro sur la page de {nom_manga}.")

        except Exception as e:
            print(f"🔥 Erreur sur {nom_manga}: {e}")

if __name__ == "__main__":
    run_scraper()
