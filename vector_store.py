from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings


class ResumeVectorStore:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.vectorstore = None

    def create_vector_store(self, text):
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100
        )
        docs = splitter.create_documents([text])
        self.vectorstore = FAISS.from_documents(docs, self.embeddings)
        return self.vectorstore

    def query(self, question):
        if self.vectorstore is None:
            return ""

        docs = self.vectorstore.similarity_search(question, k=3)
        return "\n\n".join(doc.page_content for doc in docs)