import feedparser
import psycopg2
import google.generativeai as genai
import time
import os

# ==========================================
# CONFIGURAZIONE SICURA PER IL CLOUD (NEON + GITHUB)
# ==========================================
# Il comando .strip() rimuove eventuali spazi o "a capo" invisibili
CHIAVE_API = os.environ.get("GEMINI_API_KEY", "").strip()
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

genai.configure(api_key=CHIAVE_API)
modello_ai = genai.GenerativeModel('gemini-2.5-flash') 

# ==========================================
# LISTA COMPLETA DELLE 21 FONTI GEOPOLITICHE
# ==========================================
fonti_geopolitiche = [
    {"continente": "Europa", "fonte": "BBC Europe", "url": "http://feeds.bbci.co.uk/news/world/europe/rss.xml"},
    {"continente": "Europa", "fonte": "France24", "url": "https://www.france24.com/en/europe/rss"},
    {"continente": "Europa", "fonte": "DW", "url": "https://rss.dw.com/rdf/rss-en-eu"},
    {"continente": "Nord America", "fonte": "New York Times", "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"},
    {"continente": "Nord America", "fonte": "NPR", "url": "https://feeds.npr.org/1004/rss.xml"},
    {"continente": "Nord America", "fonte": "CBC", "url": "https://www.cbc.ca/cmlink/rss-world"},
    {"continente": "Sud America", "fonte": "MercoPress", "url": "https://en.mercopress.com/rss"},
    {"continente": "Sud America", "fonte": "BBC Latin America", "url": "http://feeds.bbci.co.uk/news/world/latin_america/rss.xml"},
    {"continente": "Sud America", "fonte": "CNN Americas", "url": "http://rss.cnn.com/rss/edition_americas.rss"},
    {"continente": "Africa", "fonte": "AllAfrica", "url": "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf"},
    {"continente": "Africa", "fonte": "BBC Africa", "url": "http://feeds.bbci.co.uk/news/world/africa/rss.xml"},
    {"continente": "Africa", "fonte": "News24", "url": "https://feeds.news24.com/articles/news24/Africa/rss"},
    {"continente": "Medio Oriente", "fonte": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"continente": "Medio Oriente", "fonte": "Haaretz", "url": "https://www.haaretz.com/cmlink/1.4761404"},
    {"continente": "Medio Oriente", "fonte": "Arab News", "url": "https://www.arabnews.com/rss.xml"},
    {"continente": "Asia", "fonte": "South China Morning Post", "url": "https://www.scmp.com/rss/2/feed"},
    {"continente": "Asia", "fonte": "The Moscow Times", "url": "https://www.themoscowtimes.com/rss"},
    {"continente": "Asia", "fonte": "Yonhap", "url": "https://en.yna.co.kr/RSS/news.xml"},
    {"continente": "Oceania e Giappone", "fonte": "Kyodo News", "url": "https://english.kyodonews.net/rss/news.xml"},
    {"continente": "Oceania e Giappone", "fonte": "ABC News Australia", "url": "https://www.abc.net.au/news/feed/51120/rss.xml"},
    {"continente": "Oceania e Giappone", "fonte": "RNZ Pacific", "url": "https://www.rnz.co.nz/rss/pacific"}
]

# ==========================================
# FUNZIONI DEL SISTEMA
# ==========================================

def chiedi_all_ai(titolo, descrizione, fonte):
    """Interroga Gemini con logica di filtraggio e retry per limiti di quota."""
    prompt = f"""
    You are a professional International Geopolitics Analyst.
    Analyze this news from {fonte}.
    Original Title: {titolo}
    Description: {descrizione}
    
    CRITICAL FILTERING RULE:
    If this news is NOT strictly related to international geopolitics (e.g., local crime, sports, celebrities, or purely domestic lifestyle), respond ONLY with the word: IGNORE.
    
    If it IS relevant:
    1. Write an objective title in English (neutral tone).
    2. Write a 2-sentence summary focusing on the global strategic implications.
    
    Format:
    TITLE: [Title]
    SUMMARY: [Summary]
    """
    
    for tentativo in range(3):
        try:
            risposta = modello_ai.generate_content(prompt)
            testo = risposta.text.strip()
            if "IGNORE" in testo:
                return None 
            return testo
        except Exception as e:
            msg = str(e)
            if "429" in msg or "Quota" in msg:
                print(f"   ⏳ Limite API raggiunto. Pausa di 60 secondi (Tentativo {tentativo+1}/3)...")
                time.sleep(60)
            else:
                print(f"   ⚠️ Errore AI: {e}")
                return None
    return None

def setup_database():
    """Connessione a Neon Cloud Database (PostgreSQL)."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS notizie (
            id SERIAL PRIMARY KEY,
            titolo_originale TEXT,
            link TEXT UNIQUE,
            data_pubblicazione TEXT,
            continente TEXT,
            fonte_nome TEXT,
            testo_ai TEXT
        )
    ''')
    conn.commit()
    return conn

def raccogli_notizie():
    """Motore di aggregazione orario."""
    print("🌍 Mundiview Engine: Avvio scansione geopolitica globale...")
    
    try:
        connessione = setup_database()
        cursore = connessione.cursor()
    except Exception as e:
        print(f"❌ Errore connessione Database: {e}")
        return

    for f in fonti_geopolitiche:
        continente = f["continente"]
        nome_giornale = f["fonte"]
        url_rss = f["url"]
        print(f"📡 Analisi fonti: {nome_giornale}...")
        
        try:
            feed = feedparser.parse(url_rss)
            for articolo in feed.entries[:2]:
                titolo = articolo.title
                link = articolo.link
                descrizione = articolo.get('description', 'N/A')
                data = articolo.get('published', articolo.get('updated', 'Unknown'))
                
                cursore.execute("SELECT id FROM notizie WHERE link = %s", (link,))
                if cursore.fetchone() is None:
                    print(f"   🤖 Analisi AI: {titolo[:40]}...")
                    analisi_ai = chiedi_all_ai(titolo, descrizione, nome_giornale)
                    
                    if analisi_ai:
                        cursore.execute('''
                            INSERT INTO notizie (titolo_originale, link, data_pubblicazione, continente, fonte_nome, testo_ai)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        ''', (titolo, link, data, continente, nome_giornale, analisi_ai))
                        connessione.commit()
                        print("   ✅ Archiviata.")
                    else:
                        print("   🗑️ Scartata (Non Geopolitica).")
                    
                    # Pausa prudenziale di 15 secondi per rispettare il piano gratuito di Gemini
                    time.sleep(15)
                else:
                    print(f"   ⏭️ Già presente.")
        except Exception as e:
            print(f"⚠️ Errore con {nome_giornale}: {e}")
            
    connessione.close()
    print("\n✅ Ciclo completato. Mundiview è aggiornato.")

if __name__ == "__main__":
    raccogli_notizie()
