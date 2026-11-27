# Suivi des tâches de la bêta

Fichier de travail : il liste ce qui est **fait**, ce qui **reste**, et comment
reprendre. Mise à jour à chaque étape livrée.

Version : **0.16.0-beta2** — la stable reste **0.15.11**.

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
- [x] 46 scripts `.sh` couvrant les 24 sections de la stable.
- [x] `addons/index.json` généré (version + SHA-256).
- [x] Mise à jour sélective (`catalog.refresh`) : seuls les scripts dont la
      version augmente sont téléchargés, empreinte vérifiée, écriture atomique.
- [x] Bouton de mise à jour dans la barre latérale + signalement au lancement.
- [x] `tools/new_addon.py` pour créer un greffon conforme.

### Pages

- [x] Page générique : pastilles `●`/`◐`/`○`, infobulle nommant le manquant,
      tri par dépendances, confirmation, log en direct.
- [x] `easy` : enchaînement recommandé (dépôts → codecs → jeu).
- [x] `services` : interrupteurs `systemctl enable/disable --now` via `pkexec`.
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
- [x] `bash -n` sur les 46 scripts.
- [x] `tools/check.py` : greffons, catalogue, langues.
- [x] `tools/selftest.py` : 40 vérifications sans GTK.

---

## À faire

### Validation sur la PS5 (priorité 1)

- [ ] Lancer `python3 beta/run.py` sur la PS5 et vérifier le rendu GTK4/Adw.
- [ ] Installer un greffon `root: no` (ex. `app-btop`) : pastille, log, retour.
- [ ] Installer un greffon `root: yes` : la demande polkit s'affiche une fois.
- [ ] Vérifier `update-beta` (git pull) et le bouton de mise à jour.
- [ ] Vérifier la page Services sur un système où certains services manquent.

### Contenu

- [ ] Porter les sous-options plus fines de la stable qui n'ont pas encore de
      script dédié (au-delà des 46 livrés).
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
