# 🚀 Quick Start Guide

## Installation en 3 étapes

### 1️⃣ Installer les dépendances
```bash
pip install -r requirements.txt
```

### 2️⃣ (Optionnel) Configurer les API keys
```bash
cp .env.example .env
# Éditez .env avec vos clés API (optionnel)
```

### 3️⃣ Tester l'outil
```bash
# Test email
python main.py email test@example.com

# Test username
python main.py username johndoe

# Test téléphone
python main.py phone "+33612345678"
```

---

## 📱 Exemples Rapides

### Investigation Email
```bash
python main.py email target@domain.com
```
**Résultat**: Comptes trouvés sur 120+ sites, fuites de données, réputation

### Investigation Username
```bash
python main.py username hacker123
```
**Résultat**: Présence sur 300+ plateformes (Twitter, GitHub, Instagram, etc.)

### Investigation Téléphone
```bash
python main.py phone "+33612345678"
```
**Résultat**: Pays, opérateur, type de ligne, validation

### Mode Batch (Multiple)
```bash
python main.py batch \
  -e email1@test.com -e email2@test.com \
  -u username1 -u username2 \
  -p "+33611111111" \
  -o ./reports/batch1
```

### Mode Interactif
```bash
python main.py interactive

osint> email test@example.com
osint> username johndoe
osint> phone +33612345678
osint> quit
```

---

## 📊 Générer des Rapports

### JSON uniquement
```bash
python main.py email target@example.com -f json -o report
```

### HTML uniquement
```bash
python main.py email target@example.com -f html -o report
```

### Les deux (recommandé)
```bash
python main.py email target@example.com -f both -o report
```

---

## 🔑 API Keys (Optionnel)

Pour des résultats optimaux, obtenez ces clés gratuites:

| Service | Prix | Lien |
|---------|------|------|
| Have I Been Pwned | ~$3.50/mois | https://haveibeenpwned.com/API/Key |
| Hunter.io | 25 req/mois gratuit | https://hunter.io/api |
| Numverify | 100 req/mois gratuit | https://numverify.com/product |

**Note**: L'outil fonctionne sans clés, mais certains modules seront limités.

---

## 🎯 Cas d'Usage Principaux

### 1. Vérifier vos propres données
```bash
python main.py email votre.email@gmail.com
```
Voir où votre email est enregistré et s'il a fuité.

### 2. Pentest autorisé
```bash
python main.py batch \
  -e target@company.com \
  -u target_username \
  -o ./pentests/client_xyz
```

### 3. Due diligence
```bash
python main.py username candidate_linkedin -o ./hr/check
```

---

## ⚡ Commandes Utiles

### Verbose mode (debug)
```bash
python main.py email test@example.com -v
```

### Aide
```bash
python main.py --help
python main.py email --help
python main.py phone --help
python main.py username --help
```

---

## 📂 Où sont les résultats?

- **Rapports**: `./output/`
- **Logs**: `./logs/osint.log`

---

## ⚠️ IMPORTANT

**Usage légal uniquement:**
- ✅ Vos propres données
- ✅ Pentest avec autorisation écrite
- ✅ Recherche académique
- ❌ Harcèlement
- ❌ Stalking
- ❌ Utilisation malveillante

---

## 🆘 Problèmes?

### Erreur de module
```bash
pip install -r requirements.txt --force-reinstall
```

### Timeout
Éditez `config.yaml`:
```yaml
settings:
  timeout: 60  # augmenter
```

### Pas de résultats
```bash
# Activer mode verbose
python main.py email test@example.com -v

# Vérifier les logs
cat logs/osint.log
```

---

## 📚 Documentation Complète

- **README.md** - Documentation complète
- **USAGE.md** - Guide d'utilisation détaillé
- **config.yaml** - Configuration

---

**C'est tout! Vous êtes prêt à investiguer! 🔍**
