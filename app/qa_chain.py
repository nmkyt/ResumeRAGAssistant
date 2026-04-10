from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI


def build_qa_chain(retriever):
    """
    Собирает RAG цепочку:
    retriever + prompt + LLM
    """

    # 1. LLM (DeepSeek через OpenAI API)
    llm = ChatOpenAI(
        model="deepseek-chat",
        temperature=0
    )

    # 2. Prompt (очень важный элемент)
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""
Ты помощник по документам.

Используй ТОЛЬКО контекст ниже.
Если ответа нет — скажи "Не найдено в документах".

Контекст:
{context}

Вопрос:
{question}
"""
    )

    # 3. RAG chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type_kwargs={"prompt": prompt},
        return_source_documents=True
    )

    return qa_chain