"""Trafic simulé sur le site e-commerce d'Amazing Zone (nopCommerce sur l'App Service AmazingWeb).

Le site du Lab n'a pas de visiteurs : ce script parcourt quelques pages du catalogue, avec une part de pages
inexistantes (erreurs 404), pour que les journaux de l'App Service alimentent l'Eventstream « Flux - Journaux du site »
et l'Eventhouse pendant les tests et les captures du chapitre consacré au temps réel.

Usage :
    python trafic_simule.py --par-minute 30 --duree 10      # 30 requêtes/min pendant 10 minutes
    python trafic_simule.py --site https://…                 # autre adresse que celle du Lab
"""
import argparse
import random
import time
import urllib.error
import urllib.request
from datetime import datetime

SITE = 'https://amazingweb-e6bvejbccaerfnbt.francecentral-01.azurewebsites.net'
# Pages du catalogue de démonstration de nopCommerce, pondérées comme une navigation ordinaire
PAGES = [('/', 4), ('/computers', 3), ('/desktops', 2), ('/notebooks', 2), ('/electronics', 2), ('/cell-phones', 2),
         ('/apparel', 1), ('/books', 1), ('/jewelry', 1), ('/gift-cards', 1), ('/search?q=laptop', 1)]
TAUX_ERREUR = 0.05  # part de requêtes vers une page qui n'existe pas


def requete(site):
    if random.random() < TAUX_ERREUR:
        chemin = f'/page-introuvable-{random.randint(1, 999)}'
    else:
        chemin = random.choices([p for p, _ in PAGES], weights=[w for _, w in PAGES])[0]
    debut = time.time()
    try:
        code = urllib.request.urlopen(site + chemin, timeout=60).status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception:  # délai dépassé, connexion refusée : on le compte comme une indisponibilité
        code = 0
    return chemin, code, time.time() - debut


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--site', default=SITE)
    p.add_argument('--par-minute', type=int, default=30, help='requêtes par minute')
    p.add_argument('--duree', type=float, default=5, help='durée en minutes')
    a = p.parse_args()
    fin, total = time.time() + a.duree * 60, 0
    while time.time() < fin:
        chemin, code, duree = requete(a.site)
        total += 1
        print(f'{datetime.now():%H:%M:%S}  {code:3d}  {duree:5.2f} s  {chemin}', flush=True)
        time.sleep(max(0.0, 60 / a.par_minute - duree))
    print(f'{total} requête(s)')


if __name__ == '__main__':
    main()
