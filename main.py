from app.ingestion import load_and_split
from app.retriever import build_vectorstore, get_retriever
from app.qa_chain import build_qa_chain

# 1. ingestion
chunks = load_and_split("data/doc.pdf")

# 2. vector DB
db = build_vectorstore(chunks)

# 3. retriever
retriever = get_retriever(db)

# 4. QA chain
qa = build_qa_chain(retriever)

# 5. test
result = qa.invoke({"query": "О чем этот документ?"})

print("Ответ:")
print(result["result"])

print("\nИсточники:")
for doc in result["source_documents"]:
    print(doc.page_content[:200])
    print("-----")