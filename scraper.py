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

# Configuration pour simuler un humain sur un navigateur récent
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www.google.com/'
}

def run_scraper():
    mangas_ref = db.collection('mangas')
    mangas = mangas_ref.stream()

    for m in mangas:
        m_data = m.to_dict()
        m_id = m.id
        nom_manga = m_data.get('titre')
        url_fiche = m_data.get('url_manga')
        
        # On s'assure que dernier_connu est bien un nombre pour la comparaison
        try:
            dernier_connu = float(m_data.get('dernier_chapitre', 0))
        except:
            dernier_connu = 0.0

        if not url_fiche:
            print(f"⚠️ URL manquante pour {nom_manga}")
            continue

        print(f"🔍 Scan précis de : {nom_manga} (Format attendu: Ch. XXX)")
        try:
            response = requests.get(url_fiche, headers=HEADERS, timeout=25)
            html_content = response.text
            
            # --- REGEX SPÉCIFIQUE "Ch. 299" ---
            # Cherche "Ch." suivi d'un espace optionnel, puis un nombre (entier ou décimal)
            pattern = r"Ch\.\s*(\d+(?:\.\d+)?)"
            trouvailles = re.findall(pattern, html_content, re.IGNORECASE)
            
            if trouvailles:
                # On convertit les résultats en nombres flottants
                liste_chapitres = [float(x) for x in trouvailles]
                nouveau_chap = max(liste_chapitres)
                
                print(f"📈 Trouvé sur le site : {nouveau_chap} | Connu Firebase : {dernier_connu}")

                if nouveau_chap > dernier_connu:
                    print(f"✨ MISE À JOUR DÉTECTÉE ! {dernier_connu} -> {nouveau_chap}")
                    
                    # On cherche le lien qui contient le numéro (ex: "299")
                    soup = BeautifulSoup(html_content, 'html.parser')
                    lien_final = url_fiche
                    num_str = str(int(nouveau_chap)) if nouveau_chap.is_integer() else str(nouveau_chap)
                    
                    for a in soup.find_all('a'):
                        if num_str in a.get_text():
                            href = a.get('href', '')
                            if href:
                                if href.startswith('http'):
                                    lien_final = href
                                else:
                                    lien_final = "https://www.scan-manga.com" + href
                                break

                    # Envoi vers Firebase
                    mangas_ref.document(m_id).update({
                        'dernier_chapitre': nouveau_chap,
                        'lien_chapitre': lien_final
                    })
                else:
                    print(f"✅ {nom_manga} est déjà à jour.")
            else:
                print(f"❌ Aucun 'Ch. XXX' trouvé dans le texte. Taille HTML reçue : {len(html_content)}")
                # Si le HTML est suspectement petit (ex: < 10000), le site nous bloque
                if len(html_content) < 8000:
                    print("⚠️ Le site semble bloquer l'accès (protection anti-bot).")

        except Exception as e:
            print(f"🔥 Erreur technique : {e}")

if __name__ == "__main__":
    run_scraper()
