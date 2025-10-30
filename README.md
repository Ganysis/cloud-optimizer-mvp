# 🔍 OSINT Investigator

**Comprehensive Open Source Intelligence Toolkit**

Un outil d'OSINT complet permettant d'investiguer des emails, numéros de téléphone, et pseudos pour trouver toutes les informations publiques associées (comptes liés, mots de passe compromis, etc.).

---

## 🌟 Fonctionnalités

### 📧 Investigation Email
- **Holehe** - Vérification sur 120+ plateformes
- **Epieos** - Recherche Google Maps reviews, photos, YouTube
- **Have I Been Pwned** - Vérification de fuites de données
- **Hunter.io** - Vérification et recherche d'emails
- **EmailRep** - Réputation et analyse de risque

### 📱 Investigation Téléphone
- **PhoneInfoga** - Analyse complète (pays, opérateur, type)
- **Numverify** - Validation et métadonnées
- **TrueCaller** - Identification d'appelant
- Google Dorks automatiques

### 👤 Investigation Username
- **Sherlock** - Recherche sur 300+ plateformes
- **WhatsMyName** - Base de données étendue
- **SocialScan** - Vérification majeure plateformes
- Détection de comptes sur réseaux sociaux

### 🔐 Détection de Compromission
- Vérification HIBP (Have I Been Pwned)
- Détection de fuites de données
- Analyse de breaches multiples
- Historique de compromissions

### 📊 Rapports
- **JSON** - Format structuré pour l'analyse
- **HTML** - Rapports visuels professionnels
- Export automatique des résultats
- Historique des investigations

---

## 🚀 Installation

### Prérequis
- Python 3.8+
- pip
- Git

### Installation rapide

```bash
# Clone le repository
git clone https://github.com/votre-repo/osint-investigator.git
cd osint-investigator

# Installation des dépendances
pip install -r requirements.txt

# Configuration (optionnel mais recommandé)
cp .env.example .env
# Éditez .env avec vos clés API
```

### Configuration des API Keys (Optionnel)

Pour des résultats optimaux, obtenez des clés API gratuites:

1. **Have I Been Pwned**: https://haveibeenpwned.com/API/Key
2. **Hunter.io**: https://hunter.io/api
3. **Numverify**: https://numverify.com/product

Ajoutez-les dans `.env`:
```bash
HIBP_API_KEY=votre_cle_hibp
HUNTER_API_KEY=votre_cle_hunter
NUMVERIFY_API_KEY=votre_cle_numverify
```

---

## 📖 Utilisation

### Mode Ligne de Commande

#### Investigation Email
```bash
# Investigation simple
python main.py email example@domain.com

# Avec rapport personnalisé
python main.py email example@domain.com -o ./reports/target1 -f html

# Mode verbose (debug)
python main.py email example@domain.com -v
```

#### Investigation Téléphone
```bash
# Format international recommandé
python main.py phone "+33612345678"

# Format libre (auto-détection)
python main.py phone "0612345678"
```

#### Investigation Username
```bash
# Recherche sur toutes les plateformes
python main.py username johndoe

# Avec rapport
python main.py username johndoe -o ./reports/johndoe -f both
```

### Mode Batch (Plusieurs cibles)

```bash
# Investigation multiple
python main.py batch \
  -e email1@test.com -e email2@test.com \
  -p "+33612345678" -p "+14155552671" \
  -u johndoe -u janedoe \
  -o ./reports/batch_2024

# Formats de sortie
# -f json   : Uniquement JSON
# -f html   : Uniquement HTML
# -f both   : JSON + HTML (défaut)
```

### Mode Interactif

```bash
# Lancer le mode interactif
python main.py interactive

# Commandes disponibles:
osint> email test@example.com
osint> phone +33612345678
osint> username johndoe
osint> help
osint> quit
```

---

## 📁 Structure du Projet

```
osint-investigator/
├── main.py                          # Point d'entrée principal
├── requirements.txt                 # Dépendances Python
├── config.yaml                      # Configuration
├── .env.example                     # Template variables d'environnement
├── osint_tool/
│   ├── __init__.py
│   ├── cli.py                       # Interface ligne de commande
│   ├── core/
│   │   ├── __init__.py
│   │   └── base.py                  # Classes de base
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── email_investigator.py    # Module email
│   │   ├── phone_investigator.py    # Module téléphone
│   │   └── username_investigator.py # Module username
│   └── utils/
│       ├── __init__.py
│       ├── logger.py                # Configuration logging
│       └── reporter.py              # Génération de rapports
├── output/                          # Dossier des rapports
└── logs/                            # Fichiers de log
```

---

## 🎨 Exemples de Sorties

### Terminal
```
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              🔍 OSINT INVESTIGATOR 🔍                     ║
║                                                           ║
║       Comprehensive Open Source Intelligence Tool        ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

🔍 Starting email investigation: target@example.com

┌─────────────────── 📊 Investigation Summary ───────────────────┐
│                                                                 │
│ Target: target@example.com                                      │
│ Type: EMAIL                                                     │
│ Modules Run: 5                                                  │
│ Successful Checks: 4                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┏━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Module   ┃ Source  ┃ Status   ┃ Key Findings              ┃
┡━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Holehe   │ holehe  │ ✅ success│ Found on 12 platforms    │
│ HIBP     │ hibp    │ ✅ success│ 3 breaches, ⚠️ COMPROMISED│
│ Hunter   │ hunter  │ ✅ success│ Score: 85                │
│ EmailRep │ emailrep│ ✅ success│ Reputation: good         │
└──────────┴─────────┴──────────┴───────────────────────────┘
```

### Rapport HTML
Les rapports HTML générés sont entièrement stylisés avec:
- Design moderne et responsive
- Graphiques de synthèse
- Détails complets de chaque module
- Export et impression facilités

---

## 🔧 Configuration Avancée

### Personnalisation dans `config.yaml`

```yaml
settings:
  timeout: 30              # Timeout par requête (secondes)
  max_retries: 3          # Nombre de tentatives
  rate_limit: 60          # Requêtes par minute

modules:
  email:
    enabled: true
    tools: [holehe, epieos, hibp, hunter, emailrep]

  phone:
    enabled: true
    tools: [phoneinfoga, numverify]

  username:
    enabled: true
    tools: [sherlock, maigret, whatsmyname, socialscan]

output:
  directory: "./output"
  formats: [json, html]
  timestamp: true
```

---

## ⚠️ Avertissements Légaux

**IMPORTANT**: Cet outil est destiné UNIQUEMENT à:
- Recherches de sécurité autorisées
- Tests de pénétration avec autorisation écrite
- Investigations légales
- Recherches académiques
- Vérification de vos propres données

**INTERDIT**:
- Harcèlement ou stalking
- Utilisation malveillante
- Violation de vie privée
- Accès non autorisé
- Toute activité illégale

**L'utilisateur est seul responsable de l'utilisation de cet outil.**

---

## 🛠️ Développement

### Ajouter un nouveau module

1. Créez une nouvelle classe héritant de la classe de base appropriée:

```python
from osint_tool.core.base import EmailModule

class MonNouveauModule(EmailModule):
    def get_module_name(self) -> str:
        return "MonModule"

    async def search(self, query: str) -> Dict[str, Any]:
        # Votre logique ici
        return self.format_result(source="mon_module", data={...})
```

2. Ajoutez-le à l'investigateur correspondant dans `modules/`

### Tests

```bash
# Installation des dépendances de dev
pip install pytest pytest-asyncio pytest-cov

# Lancer les tests
pytest tests/ -v

# Avec couverture
pytest --cov=osint_tool tests/
```

---

## 🤝 Contribution

Les contributions sont les bienvenues!

1. Fork le projet
2. Créez une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit vos changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

---

## 📝 Roadmap

- [ ] Interface Web (Flask/FastAPI)
- [ ] Base de données pour historique
- [ ] API REST
- [ ] Intégration Maltego
- [ ] Support Docker
- [ ] Module de visualisation de graphes
- [ ] Détection de deepfakes
- [ ] Analyse de réseaux sociaux avancée
- [ ] Machine Learning pour corrélations
- [ ] Support multi-langues

---

## 📚 Ressources

### Outils OSINT intégrés
- [Sherlock](https://github.com/sherlock-project/sherlock)
- [Holehe](https://github.com/megadose/holehe)
- [PhoneInfoga](https://github.com/sundowndev/phoneinfoga)
- [Maigret](https://github.com/soxoj/maigret)

### APIs utilisées
- [Have I Been Pwned](https://haveibeenpwned.com/)
- [Hunter.io](https://hunter.io/)
- [EmailRep](https://emailrep.io/)

### Communauté OSINT
- [OSINT-FR](https://osintfr.com/)
- [IntelTechniques](https://inteltechniques.com/)
- [Bellingcat](https://www.bellingcat.com/)

---

## 📄 Licence

Ce projet est sous licence MIT. Voir `LICENSE` pour plus de détails.

---

## 👨‍💻 Auteurs

**Security Research Team**

---

## 🙏 Remerciements

- La communauté OSINT française (OSINT-FR)
- Tous les créateurs des outils open source intégrés
- Les contributeurs du projet

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/votre-repo/osint-investigator/issues)
- **Discussions**: [GitHub Discussions](https://github.com/votre-repo/osint-investigator/discussions)
- **Email**: security@example.com

---

**⚡ Fait avec Python et ❤️ pour la communauté OSINT**
