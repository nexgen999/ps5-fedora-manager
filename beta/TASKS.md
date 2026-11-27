# Suivi des tâches de la bêta

Fichier de travail : il liste ce qui est **fait**, ce qui **reste**, et comment
reprendre. Mise à jour à chaque étape livrée.

Version : **0.16.0-beta3** — la stable reste **0.15.11**.

---

## Fait

### Socle

- [x] Paquet `ps5m/` : `app`, `catalog`, `i18n`, `system`, `runner`, `journal`,
      `ui`, `env/`, `pages/`.
- [x] `run.py` + `VERSION` + `README.md` + `CHANGELOG.md` + ce fichier.
- [x] Aucun fichier hors de `beta/` modifié (vérifié par `git diff`).

### Greffons

- [x] Convention d'en-tête `#@` (`id`, `version`, `section`, `icon`,
      `title`/`title_fr`, `desc`/`desc_fr`, `packages`, `check_paths`, `needs`,
      `action`, `root`).
- [x] 51 scripts `.sh` couvrant les 24 sections de la stable.
- [x] `addons/index.json` généré (version + SHA-256).
- [x] Mise à jour sélective (`catalog.refresh`) : seuls les scripts dont la
      version augmente sont téléchargés, empreinte vérifiée, écriture atomique.
- [x] Bouton de mise à jour dans la barre latérale + signalement au lancement.
- [x] `tools/new_addon.py` pour créer un greffon conforme.

### Pages

- [x] Page générique : pastilles `●`/`◐`/`○`, infobulle nommant le manquant,
      tri par dépendances, confirmation, log en direct.
- [x] `easy` : enchaînement recommandé (dépôts → codecs → jeu).
- [x] `services` : un seul `systemctl show` par service (présence + `UnitFileState`),
      bascule `pkexec`, annulation polkit (code 126) sans erreur ni pastille fausse,
      services statiques et absents neutralisés.
- [x] `ui_lang` : changement de langue à chaud + couverture des traductions.
- [x] `users` : comptes humains, groupes, lecture seule.
- [x] `fedora` : version, noyau, dnf, `dnf check-update`.
- [x] Journal et À propos.

### Langues

- [x] 6 langues (fr, en, es, it, de, pt), 78 clés identiques.
- [x] Repli anglais, `direction` prévu pour le RTL.
- [x] Section `lang` : paquets `langpacks-*` pour le système.
- [x] `tools/lang_status.py` (+ `--missing xx`).

### Environnements

- [x] GNOME, KDE, Cinnamon, Budgie, générique + détection.
- [x] `supports()` pour masquer ce qu'un bureau ne sait pas faire.

### Documentation

- [x] `doc/fr/` et `doc/en/` : index, architecture, un document par module,
      langues, environnements, outils, contribuer.
- [x] `doc/{fr,en}/addons.md` généré depuis l'index (`tools/docs.py`).

### Vérifications

- [x] `py_compile` sur tout `beta/`.
- [x] `bash -n` sur les 51 scripts.
- [x] `tools/check.py` : greffons, catalogue, langues.
- [x] `tools/selftest.py` : 40 vérifications sans GTK.
- [x] `tools/import_check.py` : 25 modules importés (GTK réel si présent, factice sinon),
      intégré à `tools/check.py`.
- [x] `tools/compare_stable.py` : 149 options de la 0.15.11 comparées aux greffons,
      `doc/fr/comparaison-0.15.11.md` + `doc/en/comparison-0.15.11.md` générés.

---

## À faire

### Validation sur la PS5 (priorité 1)

- [ ] Lancer `python3 beta/run.py` sur la PS5 et vérifier le rendu GTK4/Adw.
- [ ] Installer un greffon `root: no` (ex. `app-btop`) : pastille, log, retour.
- [ ] Installer un greffon `root: yes` : la demande polkit s'affiche une fois.
- [ ] Vérifier `update-beta` (git pull) et le bouton de mise à jour.
- [ ] Vérifier la page Services sur un système où certains services manquent.

### Contenu

- [ ] Porter le catalogue Développement (`dev-build`, `dev-python-gtk`,
      `dev-containers`, `dev-virt`, `dev-rust`, `dev-cli-search`, `dev-terminal`,
      `dev-diagnostic`, `dev-debug`, `dev-python-quality`, `dev-data`,
      `dev-automation`, `dev-editors`) — 75 paquets, liste dans
      [doc/fr/manques-0.15.11.md](doc/fr/manques-0.15.11.md).
- [ ] `web-certbot` (Let's Encrypt) et `web-openssh` ; PHP / MySQL / phpMyAdmin /
      Adminer / Webmin en `install` + `remove`.
- [ ] Actions non-install listées dans [doc/fr/manques-0.15.11.md](doc/fr/manques-0.15.11.md) :
      « effacer » le journal, AppImage, pile Open WebUI, profils `easy`, gestion des
      dépôts, 10 actions de maintenance, statut/relance du ventilateur,
      vérification/désinstallation du matériel, `fix-steam`, « tout installer » en langues.
- [ ] Étendre `easy` : profils (bureautique, gaming, streaming).
- [ ] Sauvegarde / restauration des réglages.
- [ ] Export du journal en fichier.
- [ ] Recherche dans la barre latérale.
- [ ] Onglet Santé (paquets cassés, espace disque, services en échec).
- [ ] Vérification des mises à jour de la stable depuis la bêta.

### Qualité

- [ ] Relire les traductions es/it/de/pt avec un locuteur natif.
- [ ] Ajouter une langue `ja` (le fichier est déjà prévu par `lang-ja`).
- [ ] Couvrir `i18n.coverage()` et `catalog.pending()` par des cas limites
      supplémentaires.

---

## Reprendre le travail

```bash
cd ps5-fedora-manager
git pull
python3 beta/tools/check.py        # doit afficher 3 × ok
python3 beta/tools/selftest.py     # doit afficher 40 vérifications OK
python3 beta/run.py                # interface
```

Après **toute** modification d'un greffon :

```bash
python3 beta/tools/build_catalog.py && python3 beta/tools/docs.py
```

Après toute modification d'une clé de langue : `python3 beta/tools/lang_status.py`.
