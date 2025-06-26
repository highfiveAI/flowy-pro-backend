from langchain.embeddings import HuggingFaceEmbeddings

embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/distiluse-base-multilingual-cased-v2")

text = "회의 분석을 하기 위해서는 프로젝트를 먼저 생성해야합니다."

embedding_vector = embedding_model.embed_query(text)  # 텍스트 임베딩 벡터 생성 (List[float])
print(embedding_vector)  # 벡터값 확인