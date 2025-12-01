"""ChromaDB içeriğini görüntüleme scripti"""
from src.database.vector_store import VectorStore

def view_collections():
    """ChromaDB'deki tüm collection'ları ve içeriklerini görüntüle"""
    vs = VectorStore()
    
    # Solutions collection
    print("\n" + "="*60)
    print("📦 SOLUTIONS COLLECTION")
    print("="*60)
    
    try:
        solutions = vs.solutions.get()
        print(f"\n📊 Toplam döküman sayısı: {len(solutions['ids'])}")
        
        if solutions['ids']:
            for i, (doc_id, doc, metadata) in enumerate(zip(
                solutions['ids'], 
                solutions['documents'], 
                solutions['metadatas']
            )):
                print(f"\n--- Döküman {i+1} ---")
                print(f"🆔 ID: {doc_id}")
                print(f"📝 İçerik: {doc[:200]}..." if len(doc) > 200 else f"📝 İçerik: {doc}")
                print(f"🏷️  Metadata: {metadata}")
        else:
            print("❌ Henüz kayıtlı çözüm yok.")
    except Exception as e:
        print(f"❌ Hata: {e}")
    
    # Conversations collection
    print("\n" + "="*60)
    print("💬 CONVERSATIONS COLLECTION")
    print("="*60)
    
    try:
        convos = vs.conversations.get()
        print(f"\n📊 Toplam döküman sayısı: {len(convos['ids'])}")
        
        if convos['ids']:
            for i, (doc_id, doc, metadata) in enumerate(zip(
                convos['ids'], 
                convos['documents'], 
                convos['metadatas']
            )):
                print(f"\n--- Döküman {i+1} ---")
                print(f"🆔 ID: {doc_id}")
                print(f"📝 İçerik: {doc[:200]}..." if len(doc) > 200 else f"📝 İçerik: {doc}")
                print(f"🏷️  Metadata: {metadata}")
        else:
            print("❌ Henüz kayıtlı konuşma yok.")
    except Exception as e:
        print(f"❌ Hata: {e}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    view_collections()
