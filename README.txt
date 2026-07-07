# TELEGRAM SOCIAL DOWNLOADER BOT - GUIDA COMPLETA

## CONTENUTO DEL PROGETTO

La cartella contiene:

1. **bot.py** - Il codice principale del bot
2. **requirements.txt** - Le dipendenze Python necessarie
3. **Dockerfile** e **Procfile** - File per il deploy
4. **README.md** e **DEPLOY_GUIDE.txt** - Documentazione

---

## COSA DEVI FARE TU

### Step 1: Ottieni il Bot Token
1. Apri **Telegram** e cerca **@BotFather**
2. Invia il comando `/newbot`
3. Dai un nome al bot (es: "DownloadBot")
4. Dai un username (deve finire con `bot`, es: `mioDownloadBot`)
5. **Copia il Token** che ti viene fornito (formato: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### Step 2: Inserisci il Token nel bot
Non inserire il token dentro `bot.py`.

Usa una variabile ambiente:

```bash
export BOT_TOKEN="il_tuo_token"
```

In alternativa, crea un file `.env` locale con:

```bash
BOT_TOKEN=il_tuo_token
```

Il file `.env` e' ignorato da Git.

### Step 3: Installa le dipendenze
Apri un terminale e naviga nella cartella:
```bash
cd ~/telegram-download-bot
pip install -r requirements.txt
```

### Step 4: Avvia il bot
```bash
python3 bot.py
```

### Step 5: Usa il bot
1. Cerca il tuo bot su Telegram (con l'username che hai scelto)
2. Invia `/start` per iniziare
3. Invia un link (YouTube, Pinterest, Instagram, ecc.)
4. Il bot scaricherà e ti invierà il file

---

## PIATTAFORME SUPPORTATE

Il bot supporta principalmente:

✅ YouTube / YouTube Music
✅ Pinterest
✅ Instagram
✅ TikTok
✅ Twitter / X
✅ Facebook
✅ Threads
✅ Spotify audio

---

## NOTE IMPORTANTI

- **Limite Telegram**: 50MB per i file (se il video è più grande, il bot avviserà)
- **Velocità**: Dipende dalla tua connessione e dal server del video
- **GPU**: Non richiede GPU, funziona su qualsiasi PC

---

## COMANDI DEL BOT

- `/start` - Avvia il bot
- `/support` - Mostra il contatto di supporto

---

## RISOLUZIONE PROBLEMI

### Errore "python-telegram-bot not found"
```bash
pip install python-telegram-bot
```

### Errore "yt-dlp not found"
```bash
pip install yt-dlp
```

### Il bot non risponde
- Verifica che il token sia corretto
- Verifica che la variabile `BOT_TOKEN` sia impostata
- Riavvia il bot con Ctrl+C e di nuovo `python3 bot.py`

### Errore "BOT_TOKEN is missing"
Imposta `BOT_TOKEN` come variabile ambiente o nel file `.env`.

---

## AUTO-AVvio (opzionale)

Se vuoi che il bot parta automaticamente all'accensione del PC, aggiungi questo alle applicazioni d'avvio:
```bash
cd ~/telegram-download-bot && python3 bot.py
```

---

Creato il: 2026-03-20
Posizione: Telegram-VM-Bot/
