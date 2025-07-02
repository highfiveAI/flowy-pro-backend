from langchain.embeddings import HuggingFaceEmbeddings

embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/distiluse-base-multilingual-cased-v2")

text = "사이트"

embedding_vector = embedding_model.embed_query(text)  # 텍스트 임베딩 벡터 생성 (List[float])
print(embedding_vector)  # 벡터값 확인
print(len(embedding_vector))