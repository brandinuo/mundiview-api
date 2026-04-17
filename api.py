from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3

app = FastAPI()

# Questo permette al tuo sito web di parlare con la tua API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/notizie")
def leggi_notizie():
    connessione = sqlite3.connect('geopolitica.db')
    # Permette di accedere ai dati tramite nome della colonna
    connessione.row_factory = sqlite3.Row 
    cursore = connessione.cursor()
    
    cursore.execute("SELECT * FROM notizie ORDER BY id DESC")
    righe = cursore.fetchall()
    
    # Trasformiamo i dati in una lista di dizionari (formato JSON)
    risultato = [dict(r) for r in righe]
    
    connessione.close()
    return risultato

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)