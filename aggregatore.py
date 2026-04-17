import feedparser
import sqlite3
import google.generativeai as genai
import time

# ==========================================
# CONFIGURAZIONE INTELLIGENZA ARTIFICIALE
# ==========================================
# INSERISCI QUI LA TUA CHIAVE API DI GOOGLE STUDIO
CHIAVE_API = "AQ.Ab8RN6JJYCMnbbSEEb178Ec179VN06P_Q4N3_poqkFYPV6zbBQ"
genai.configure(api_key=CHIAVE_API)
modello_ai = genai.GenerativeModel('gemini-2.5-flash') 

# ==========================================
# LISTA GLOBALE DELLE FONTI GEOPOLITICHE
# ==========================================
fonti_geopolitiche = [
    # EUROPA
    {"continente": "Europa", "fonte": "BBC Europe", "url": "http://feeds.bbci.co.uk/news/world/europe/rss.xml"},
    {"continente": "Europa", "fonte": "France24", "url": "https://www.france24.com/en/europe/rss"},
    {"continente": "Europa", "fonte": "DW", "url": "https://rss.dw.com/rdf/rss-en-eu"},
    
    # NORD AMERICA
    {"continente": "Nord America", "fonte": "New York Times", "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"},
    {"continente": "Nord America", "fonte": "NPR", "url": "https://feeds.npr.org/1004/rss.xml"},
    {"continente": "Nord America", "fonte": "CBC", "url": "https://www.cbc.ca/cmlink/rss-world"},
    
    # SUD AMERICA
    {"continente": "Sud America", "fonte": "MercoPress", "url": "https://en.mercopress.com/rss"},
    {"continente": "Sud America", "fonte": "BBC Latin America", "url": "http://feeds.bbci.co.uk/news/world/latin_america/rss.xml"},
    {"continente": "Sud America", "fonte": "CNN Americas", "url": "http://rss.cnn.com/rss/edition_americas.rss"},
    
    # AFRICA
    {"continente": "Africa", "fonte": "AllAfrica", "url": "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf"},
    {"continente": "Africa", "fonte": "BBC Africa", "url": "http://feeds.bbci.co.uk/news/world/africa/rss.xml"},
    {"continente": "Africa", "fonte": "News24", "url": "https://feeds.news24.com/articles/news24/Africa/rss"},
    
    # MEDIO ORIENTE
    {"continente": "Medio Oriente", "fonte": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"continente": "Medio Oriente", "fonte": "Haaretz", "url": "https://www.haaretz.com/cmlink/1.4761404"},
    {"continente": "Medio Oriente", "fonte": "Arab News", "url": "https://www.arabnews.com/rss.xml"},
    
    # ASIA
    {"continente": "Asia", "fonte": "South China Morning Post", "url": "https://www.scmp.com/rss/2/feed"},
    {"continente": "Asia", "fonte": "The Moscow Times", "url": "https://www.themoscowtimes.com/rss"},
    {"continente": "Asia", "fonte": "Yonhap", "url": "https://en.yna.co.kr/RSS/news.xml"},
    
    # OCEANIA E GIAPPONE
    {"continente": "Oceania e Giappone", "fonte": "Kyodo News", "url": "https://english.kyodonews.net/rss/news.xml"},
    {"continente": "Oceania e Giappone", "fonte": "ABC News Australia", "url": "https://www.abc.net.au/news/feed/51120/rss.xml"},
    {"continente": "Oceania e Giappone", "fonte": "RNZ Pacific", "url": "https://www.rnz.co.nz/rss/pacific"}
]

# ==========================================
# FUNZIONI DEL SISTEMA
# ==========================================
def chiedi_all_ai(titolo, descrizione, fonte):
    """L'AI analizza la notizia ed estrae i fatti in un inglese neutrale."""
    prompt = f"""
    You are an objective and neutral geopolitical analyst.
    Read the following news item from {fonte}.
    Original Title: {titolo}
    Brief Description: {descrizione}
    
    Task:
    1. Write a clear, objective title in English. Remove any sensationalism or bias from the original source.
    2. Write a concise summary (maximum 2 sentences) in English. Focus strictly on facts, geopolitical implications, and keep a completely neutral tone.
    
    Respond EXACTLY in this format:
    TITLE: [Your objective title]
    SUMMARY: [Your neutral summary]
    """
    try:
        risposta = modello_ai.generate_content(prompt)
        return risposta.text
    except Exception as e:
        return f"TITLE: {titolo}\nSUMMARY: AI Summary unavailable due to error ({e})"

def setup_database():
    """Inizializza il database e crea la tabella se non esiste."""
    connessione = sqlite3.connect('geopolitica.db')
    cursore = connessione.cursor()
    cursore.execute('''
        CREATE TABLE IF NOT EXISTS notizie (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titolo_originale TEXT,
            link TEXT UNIQUE,
            data_pubblicazione TEXT,
            continente TEXT,
            fonte_nome TEXT,
            testo_ai TEXT
        )
    ''')
    connessione.commit()
    return connessione

def raccogli_notizie():
    """Motore principale di aggregazione."""
    print("🌍 Avvio del Global Geopolitical Aggregator...")
    print("⚠️ Attenzione: l'analisi dell'intero globo richiederà alcuni minuti a causa dei limiti di velocità dell'AI.\n")
    
    connessione = setup_database()
    cursore = connessione.cursor()
    
    for f in fonti_geopolitiche:
        continente = f["continente"]
        nome_giornale = f["fonte"]
        url_rss = f["url"]
        
        print(f"📡 Lettura da: {nome_giornale} ({continente})")
        
        try:
            feed = feedparser.parse(url_rss)
            
            # Estraiamo le prime 2 notizie per ogni fonte (totale 42 notizie per ciclo)
            for articolo in feed.entries[:2]:
                titolo = articolo.title
                link = articolo.link
                descrizione = articolo.get('description', 'No description available')
                data = articolo.get('published', articolo.get('updated', 'Unknown date'))
                
                # Controlla se la notizia è già nel database
                cursore.execute("SELECT id FROM notizie WHERE link = ?", (link,))
                if cursore.fetchone() is None:
                    print(f"   🤖 Elaborazione AI in corso per: '{titolo[:30]}...'")
                    
                    analisi_ai = chiedi_all_ai(titolo, descrizione, nome_giornale)
                    
                    cursore.execute('''
                        INSERT INTO notizie (titolo_originale, link, data_pubblicazione, continente, fonte_nome, testo_ai)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (titolo, link, data, continente, nome_giornale, analisi_ai))
                    connessione.commit()
                    
                    # ⏱️ PAUSA CRITICA: 5 secondi per evitare il blocco (Error 429 Too Many Requests)
                    time.sleep(5) 
                else:
                    print(f"   ⏭️ Già in archivio, passo alla prossima.")
                
        except Exception as e:
            print(f"⚠️ Errore di connessione con {nome_giornale}: {e}")
            
    connessione.close()
    print("\n✅ Analisi globale completata con successo! Dati salvati in geopolitica.db")

if __name__ == "__main__":
    raccogli_notizie()