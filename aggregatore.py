import feedparser
import psycopg2
import google.generativeai as genai
import time
import os

# ==========================================
# CONFIGURAZIONE SICURA PER IL CLOUD
# ==========================================
# Le chiavi ora vengono prese dai "Segreti" di GitHub e Render, non sono più scritte qui!
CHIAVE_API = os.environ.get("GEMINI_API_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")

genai.configure(api_key=CHIAVE_API)
modello_ai = genai.GenerativeModel('gemini-2.5-flash') 

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

def chiedi_all_ai(titolo, descrizione, fonte):
    prompt = f"""
    You are a professional International Geopolitics Analyst.
    Analyze this news from {fonte}.
    
    Original Title: {titolo}
    Description: {descrizione}
    
    CRITICAL FILTERING RULE:
    If this news is NOT strictly related to international geopolitics (e.g., local crime, sports, domestic politics), respond ONLY with: IGNORE.
    
    If relevant:
    1. Write an objective title in English.
    2. Write a 2-sentence summary focusing on global implications.
    
    Format:
    TITLE: [Title]
    SUMMARY: [Summary]
    """
    try:
        risposta = modello_ai.generate_content(prompt)
        testo = risposta.text.strip()
        if "IGNORE" in testo:
            return None 
        return testo
    except Exception as e:
        print(f"Errore AI: {e}")
        return None

def setup_database():
    """Si connette a Neon (PostgreSQL)"""
    connessione = psycopg2.connect(DATABASE_URL)
    cursore = connessione.cursor()
    cursore.execute('''
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
    connessione.commit()
    return connessione

def raccogli_notizie():
    print("🌍 Avvio del Motore Cloud Mundiview...")
    connessione = setup_database()
    cursore = connessione.cursor()
    
    for f in fonti_geopolitiche:
        continente = f["continente"]
        nome_giornale = f["fonte"]
        url_rss = f["url"]
        print(f"📡 Lettura da: {nome_giornale}")
        
        try:
            feed = feedparser.parse(url_rss)
            for articolo in feed.entries[:2]:
                titolo = articolo.title
                link = articolo.link
                descrizione = articolo.get('description', 'No description')
                data = articolo.get('published', articolo.get('updated', 'Unknown date'))
                
                # In PostgreSQL si usa %s invece di ?
                cursore.execute("SELECT id FROM notizie WHERE link = %s", (link,))
                if cursore.fetchone() is None:
                    analisi_ai = chiedi_all_ai(titolo, descrizione, nome_giornale)
                    
                    if analisi_ai:
                        cursore.execute('''
                            INSERT INTO notizie (titolo_originale, link, data_pubblicazione, continente, fonte_nome, testo_ai)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        ''', (titolo, link, data, continente, nome_giornale, analisi_ai))
                        connessione.commit()
                        print("   ✅ Salvata in Cloud.")
                        time.sleep(5) 
                    else:
                        print("   🗑️ Scartata.")
                        time.sleep(2)
        except Exception as e:
            print(f"⚠️ Errore con {nome_giornale}: {e}")
            
    connessione.close()
    print("\n✅ Analisi e salvataggio su Neon completato!")

if __name__ == "__main__":
    raccogli_notizie()