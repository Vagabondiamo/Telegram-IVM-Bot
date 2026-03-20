# TELEGRAM VIDEO DOWNLOAD BOT - GUIDA COMPLETA

## COSA HO FATTO

Ho creato una cartella `telegram-download-bot` nella tua home contenente:

1. **bot.py** - Il codice principale del bot
2. **requirements.txt** - Le dipendenze Python necessarie

---

## COSA DEVI FARE TU

### Step 1: Ottieni il Bot Token
1. Apri **Telegram** e cerca **@BotFather**
2. Invia il comando `/newbot`
3. Dai un nome al bot (es: "DownloadBot")
4. Dai un username (deve finire con `bot`, es: `mioDownloadBot`)
5. **Copia il Token** che ti viene fornito (formato: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### Step 2: Inserisci il Token nel bot
Apri il file `bot.py` e sostituisci questa riga:
```python
BOT_TOKEN = "INSERISCI_QUI_IL_TUO_TOKEN"
```
Con il tuo token reale:
```python
BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
```

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

Il bot supporta **1500+ siti** grazie a yt-dlp e gallery-dl:

✅ YouTube / YouTube Music
✅ Pinterest
✅ Instagram
✅ TikTok
✅ Twitter / X
✅ Facebook
✅ Reddit
✅ Vimeo
✅ Dailymotion
✅ SoundCloud
✅ E molti altri...

---

## NOTE IMPORTANTI

- **Limite Telegram**: 50MB per i file (se il video è più grande, il bot avviserà)
- **Velocità**: Dipende dalla tua connessione e dal server del video
- **GPU**: Non richiede GPU, funziona su qualsiasi PC

---

## COMANDI DEL BOT

- `/start` - Avvia il bot
- `/help` - Mostra l'aiuto

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
- Verifica che il bot sia avviato (terminale deve mostrare "Bot pronto!")
- Riavvia il bot con Ctrl+C e di nuovo `python3 bot.py`

---

## AUTO-AVvio (opzionale)

Se vuoi che il bot parta automaticamente all'accensione del PC, aggiungi questo alle applicazioni d'avvio:
```bash
cd ~/telegram-download-bot && python3 bot.py
```

---

Creato il: 2026-03-20
Posizione: ~/telegram-download-bot/
