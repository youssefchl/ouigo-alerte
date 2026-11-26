"""Vérifie UNE fois la page OUIGOSWAP et envoie une notif ntfy si un billet
apparaît (prix max réglé dans l'URL via maxPrice, heure mini via HEURE_MIN).
Lancé automatiquement par GitHub Actions."""

import os
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from playwright.sync_api import sync_playwright

URL = os.environ["URL_RECHERCHE"]
TOPIC = os.environ["NTFY_TOPIC"]
TEXTE_SI_VIDE = os.environ.get("TEXTE_SI_VIDE") or "Pas de résultat"
HEURE_MIN = os.environ.get("HEURE_MIN") or "00:00"   # 00:00 = toutes les heures
ARRET_LE = datetime(2026, 12, 20, 23, 0, tzinfo=ZoneInfo("Europe/Paris"))

# Repères dans la page : les billets sont entre DEBUT et FIN
DEBUTS = ["Consulter nos équipements à bord", "Le plus tôt"]
FINS = ["D’autres idées", "D'autres idées"]


def notifier(titre, message, priorite="urgent"):
    requests.post(
        f"https://ntfy.sh/{TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": titre.encode("utf-8"), "Priority": priorite,
                 "Tags": "train", "Click": URL},
        timeout=10,
    )


def zone_resultats(texte):
    """Garde uniquement la partie de la page où sont listés les billets."""
    debut = 0
    for d in DEBUTS:
        i = texte.find(d)
        if i != -1:
            debut = i + len(d)
            break
    fin = len(texte)
    for f in FINS:
        j = texte.find(f, debut)
        if j != -1:
            fin = j
            break
    return texte[debut:fin]


def heures(texte):
    """Trouve les heures du type 16:25 ou 16h25, dans l'ordre d'apparition."""
    return [f"{int(h):02d}:{m}" for h, m in
            re.findall(r"\b([01]?\d|2[0-3])\s*[:hH]\s*([0-5]\d)\b", texte)]


if datetime.now(ZoneInfo("Europe/Paris")) > ARRET_LE:
    print("Date dépassée, rien à faire.")
    sys.exit(0)

if os.environ.get("TEST") == "1":
    notifier("Test OUIGOSWAP", "La connexion GitHub -> téléphone marche ✅", "default")

with sync_playwright() as p:
    nav = p.chromium.launch()
    page = nav.new_page(locale="fr-FR")
    page.goto(URL, wait_until="networkidle", timeout=60_000)
    page.wait_for_timeout(5000)
    texte = page.inner_text("body")
    nav.close()

if TEXTE_SI_VIDE.lower() in texte.lower():
    print(">> Rien pour l'instant.")
    sys.exit(0)

zone = zone_resultats(texte)
print("=== ZONE DES RÉSULTATS ===")
print(zone[:2000])
print("==========================")

toutes = heures(zone)
departs = toutes[0::2]   # chaque billet : heure de départ puis heure d'arrivée
print(f"Heures trouvées : {toutes}")
print(f"Départs supposés : {departs}")

if not toutes:
    print(">> Billet trouvé mais heure illisible -> alerte par sécurité")
    notifier("🚄 Billet OUIGOSWAP dispo !",
             "Un billet moins cher est dispo (heure non lue). Fonce vérifier !")
    sys.exit(0)

bons = [h for h in departs if h >= HEURE_MIN]
if bons:
    print(f">> BILLET DISPO : départs {bons}")
    notifier("🚄 Billet OUIGOSWAP moins cher !",
             f"Paris -> Strasbourg 20/12, départ {', '.join(bons)}. Fonce !")
else:
    print(f">> Billets dispo mais tous avant {HEURE_MIN} : {departs} -> pas d'alerte")
