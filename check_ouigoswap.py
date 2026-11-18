"""Vérifie UNE fois la page OUIGOSWAP et envoie une notif ntfy si un billet apparaît.
Lancé automatiquement toutes les ~5 min par GitHub Actions."""

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from playwright.sync_api import sync_playwright

URL = os.environ["URL_RECHERCHE"]
TOPIC = os.environ["NTFY_TOPIC"]
TEXTE_SI_VIDE = os.environ.get("TEXTE_SI_VIDE", "Aucun billet")
ARRET_LE = datetime(2026, 11, 20, 23, 0, tzinfo=ZoneInfo("Europe/Paris"))


def notifier(titre, message, priorite="urgent"):
    requests.post(
        f"https://ntfy.sh/{TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": titre.encode("utf-8"), "Priority": priorite,
                 "Tags": "train", "Click": URL},
        timeout=10,
    )


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

print(texte[:1500])  # visible dans les logs GitHub pour vérifier

if TEXTE_SI_VIDE.lower() in texte.lower():
    print(">> Rien pour l'instant.")
else:
    print(">> BILLET POSSIBLE !")
    notifier("🚄 Billet OUIGOSWAP dispo !", "Paris -> Strasbourg 20/11 : fonce sur OUIGOSWAP !")
