# Outils

Tous les scripts sont dans `beta/tools/` et s'exécutent depuis la racine du
dépôt.

| Commande | Rôle |
|---|---|
| `python3 beta/tools/check.py` | en-têtes, ids uniques, `needs` valides, `bash -n`, index à jour, langues |
| `python3 beta/tools/selftest.py` | logique pure : versions, dépendances, index, langues, environnements, chemins, journal |
| `python3 beta/tools/build_catalog.py` | régénère `addons/index.json` |
| `python3 beta/tools/build_catalog.py --check` | échoue si l'index n'est pas à jour |
| `python3 beta/tools/lang_status.py` | couverture par langue |
| `python3 beta/tools/lang_status.py --missing xx` | clés absentes d'une langue |
| `python3 beta/tools/docs.py` | régénère `doc/{fr,en}/addons.md` |
| `python3 beta/tools/new_addon.py` | crée un greffon à partir de quelques options |
| `python3 beta/tools/import_check.py` | importe tous les modules (GTK réel ou factice) |
| `python3 beta/tools/compare_stable.py` | compare les options de `ps5_manager.py` aux greffons |

## Exemple : nouvel addon

```bash
python3 beta/tools/new_addon.py --id app-htop --section library \
  --packages "htop" --title-en "htop" --title-fr "htop" \
  --desc-en "Process viewer." --desc-fr "Visionneuse de processus."
python3 beta/tools/build_catalog.py
python3 beta/tools/docs.py
python3 beta/tools/check.py
```

Pour un greffon qui n'installe pas de paquets : `--body-file body.sh` avec le
contenu du script et `--check-paths /chemin/attendu`.
