# Guide d'Utilisation OSINT Investigator

## 🎯 Démarrage Rapide

### Installation

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Rendre le script exécutable (optionnel)
chmod +x main.py

# 3. Configuration (optionnel)
cp .env.example .env
# Éditez .env avec vos clés API
```

---

## 📧 Investigation Email

### Exemple basique
```bash
python main.py email test@example.com
```

### Ce qui est vérifié:
- ✅ Comptes sur 120+ plateformes (Instagram, Twitter, GitHub, etc.)
- ✅ Fuites de données (Have I Been Pwned)
- ✅ Réputation de l'email
- ✅ Vérification SMTP
- ✅ Domaine et enregistrements MX

### Résultats typiques:
```
Found on 12 platforms
3 breaches detected ⚠️
Email reputation: good
SMTP valid: true
```

### Avec rapport personnalisé:
```bash
# Générer rapport HTML uniquement
python main.py email target@domain.com -f html -o ./reports/investigation1

# Générer JSON + HTML
python main.py email target@domain.com -f both -o ./reports/investigation1
```

---

## 📱 Investigation Téléphone

### Formats acceptés:
```bash
# Format international (recommandé)
python main.py phone "+33612345678"

# Format national
python main.py phone "0612345678"

# Format avec espaces
python main.py phone "+1 415 555 2671"
```

### Ce qui est vérifié:
- ✅ Pays d'origine
- ✅ Opérateur télécom
- ✅ Type de ligne (mobile, fixe, VOIP)
- ✅ Fuseaux horaires
- ✅ Validité du numéro
- ✅ Recherches Google automatiques

### Résultats typiques:
```
Valid: true
Country: France
Carrier: Orange France
Line Type: MOBILE
Timezone: Europe/Paris
```

---

## 👤 Investigation Username

### Exemple basique:
```bash
python main.py username johndoe
```

### Ce qui est vérifié:
- ✅ 300+ plateformes sociales
- ✅ Sites de développeurs (GitHub, GitLab)
- ✅ Forums et communautés
- ✅ Sites de gaming
- ✅ Plateformes de contenu
- ✅ Services professionnels

### Plateformes couvertes:
- **Réseaux sociaux**: Instagram, Twitter, Facebook, TikTok, LinkedIn
- **Développement**: GitHub, GitLab, Stack Overflow, Dev.to
- **Gaming**: Steam, Xbox, PlayStation, Twitch
- **Contenu**: YouTube, Medium, Patreon, OnlyFans
- **Professionnel**: LinkedIn, AngelList, Behance
- **Autres**: Reddit, Pinterest, Telegram, Discord

### Résultats typiques:
```
Found on 45 sites:
1. GitHub: https://github.com/johndoe
2. Twitter: https://twitter.com/johndoe
3. Instagram: https://instagram.com/johndoe
...
```

---

## 🔄 Mode Batch (Multiple Targets)

### Investigation de plusieurs cibles simultanément:

```bash
python main.py batch \
  -e email1@example.com \
  -e email2@example.com \
  -e email3@example.com \
  -p "+33612345678" \
  -p "+14155552671" \
  -u johndoe \
  -u janedoe \
  -u hacker123 \
  -o ./reports/batch_investigation \
  -f both
```

### Options batch:
- `-e` / `--email` : Emails à investiguer (multiple)
- `-p` / `--phone` : Numéros à investiguer (multiple)
- `-u` / `--username` : Usernames à investiguer (multiple)
- `-o` / `--output` : Dossier de sortie
- `-f` / `--format` : Format (json, html, both)

---

## 💬 Mode Interactif

### Lancer le mode interactif:
```bash
python main.py interactive
```

### Commandes disponibles:

```
osint> email test@example.com
osint> phone +33612345678
osint> username johndoe
osint> help
osint> quit
```

### Avantages:
- Session persistante
- Pas besoin de relancer le script
- Historique des commandes
- Plus rapide pour plusieurs investigations

---

## 📊 Formats de Sortie

### JSON
```bash
python main.py email test@example.com -f json -o report
```

Génère: `report.json`
- Format structuré
- Facile à parser
- Idéal pour automatisation

### HTML
```bash
python main.py email test@example.com -f html -o report
```

Génère: `report.html`
- Visuel et professionnel
- Facile à lire
- Imprimable
- Partageable

### Les deux
```bash
python main.py email test@example.com -f both -o report
```

Génère: `report.json` + `report.html`

---

## 🔑 Configuration des API Keys

### Clés recommandées (gratuites):

#### 1. Have I Been Pwned
```bash
# Obtenir la clé: https://haveibeenpwned.com/API/Key
# Prix: ~$3.50/mois
echo 'HIBP_API_KEY=votre_cle' >> .env
```

**Bénéfice**: Vérification de fuites de données

#### 2. Hunter.io
```bash
# Obtenir la clé: https://hunter.io/api
# Plan gratuit: 25 requêtes/mois
echo 'HUNTER_API_KEY=votre_cle' >> .env
```

**Bénéfice**: Vérification et recherche d'emails

#### 3. Numverify
```bash
# Obtenir la clé: https://numverify.com/product
# Plan gratuit: 100 requêtes/mois
echo 'NUMVERIFY_API_KEY=votre_cle' >> .env
```

**Bénéfice**: Validation avancée de téléphone

### Sans clés API:
L'outil fonctionne quand même! Mais certains modules seront limités.

---

## 🎨 Options Avancées

### Mode Verbose (Debug)
```bash
# Afficher tous les détails
python main.py email test@example.com -v

# Logs détaillés dans ./logs/osint.log
```

### Personnaliser la configuration
Éditez `config.yaml`:

```yaml
settings:
  timeout: 30        # Augmenter pour connexions lentes
  max_retries: 3     # Nombre de tentatives
  rate_limit: 60     # Requêtes par minute

modules:
  email:
    enabled: true
    tools: [holehe, hibp, hunter]  # Sélectionner modules
```

---

## 📋 Cas d'Usage

### 1. Vérifier vos propres comptes
```bash
# Voir où votre email est enregistré
python main.py email votre.email@gmail.com

# Vérifier compromissions
# Résultat: "Found on 23 platforms, 2 breaches"
```

### 2. Investigation de sécurité autorisée
```bash
# Pentest d'un client (avec autorisation)
python main.py batch \
  -e target@company.com \
  -p "+33XXXXXXXXX" \
  -u targetusername \
  -o ./pentests/client_xyz
```

### 3. Recherche académique
```bash
# Étude sur présence digitale
python main.py username researcher123 -o ./research/subject1
```

### 4. Due diligence
```bash
# Vérification avant embauche (avec consentement)
python main.py batch \
  -e candidate@email.com \
  -u candidate_linkedin \
  -o ./hr/candidate_check
```

---

## ⚡ Trucs & Astuces

### 1. Alias pour utilisation rapide
```bash
# Ajoutez dans ~/.bashrc ou ~/.zshrc
alias osint='python /path/to/main.py'
alias osint-email='python /path/to/main.py email'
alias osint-phone='python /path/to/main.py phone'
alias osint-user='python /path/to/main.py username'

# Utilisation:
osint-email test@example.com
```

### 2. Investigations planifiées
```bash
# Créer un cron job pour monitoring
# Fichier: /etc/cron.daily/osint-check
#!/bin/bash
python /path/to/main.py email monitor@company.com -o /var/reports/daily
```

### 3. Combiner avec autres outils
```bash
# Export JSON pour traitement
python main.py email target@example.com -f json -o data
cat data.json | jq '.results[] | select(.status=="success")'
```

### 4. Investigation approfondie
```bash
# 1. Commencer par email
python main.py email target@example.com -o reports/target

# 2. Examiner le rapport pour trouver usernames
# 3. Investiguer chaque username trouvé
python main.py username discovered_username -o reports/target_username

# 4. Chercher numéros de téléphone dans résultats
python main.py phone "+33XXXXXXXXX" -o reports/target_phone
```

---

## 🚨 Résolution de Problèmes

### Erreur: Module non trouvé
```bash
# Réinstaller dépendances
pip install -r requirements.txt --force-reinstall
```

### Timeout sur certains sites
```bash
# Augmenter le timeout dans config.yaml
settings:
  timeout: 60  # Passer de 30 à 60
```

### Rate limiting
```bash
# Réduire le rate limit dans config.yaml
settings:
  rate_limit: 30  # Passer de 60 à 30
```

### Pas de résultats
- Vérifiez l'orthographe du target
- Essayez différents formats (email, username)
- Activez mode verbose: `-v`
- Vérifiez les logs: `./logs/osint.log`

---

## 📞 Support

**Besoin d'aide?**
- Documentation: README.md
- Issues: GitHub Issues
- Email: support@example.com

---

**Bon OSINT! 🔍**
