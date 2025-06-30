from langchain.embeddings import HuggingFaceEmbeddings

embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/distiluse-base-multilingual-cased-v2")

text = "로그인을 하시기 위해서는 관리자의 승인이 된 계정이여야 합니다. 만약 계정을 만들고 싶으시면 회원가입 페이지로 안내를 하겠습니다."

embedding_vector = embedding_model.embed_query(text)  # 텍스트 임베딩 벡터 생성 (List[float])
print(embedding_vector)  # 벡터값 확인
print(len(embedding_vector))