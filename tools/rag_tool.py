from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")

import logging  # Import Python's built-in logging module

os.makedirs("logs", exist_ok=True)  # Create a "logs" directory if it doesn't exist

logger = logging.getLogger("file_api_logger")  # Create a custom logger named "file_api_logger"
logger.setLevel(logging.INFO)  # Set logging level to INFO

file_handler = logging.FileHandler("logs/app.log")  # Log messages will be written to logs/app.log

formatter = logging.Formatter(  # Define the format of log messages
    "%(asctime)s, %(api_path)s, %(levelname)s, %(message)s",
    datefmt="%Y-%m-%d, %H:%M:%S"
)

file_handler.setFormatter(formatter)  # Attach the formatter to the file handler
logger.addHandler(file_handler)  # Add the file handler to the logger



#cleans the text
def clean_text(text):
    import re
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


from langchain_community.document_loaders import PyPDFLoader

#file path
pdf_path = "data/attention.pdf"

#loading the pdf
loader = PyPDFLoader(pdf_path)
logger.info(f"Loading PDF: {pdf_path}", extra={"api_path": "load_pdf"})
documents = loader.load()
logger.info(f"{len(documents)} pages loaded.", extra={"api_path": "load_pdf"})
            
        
#page numbers % content example
print(f"{len(documents)} pages loaded.")
#print(documents[0].page_content[:500]) it worked.

low_text_pages = []

#checking the character numbers of each page(pypdfloader)
for i, doc in enumerate(documents):
    text_length = len(doc.page_content.strip())
    if text_length < 1500: 
        #print(f"Page {i + 1} has low text ({text_length} chars)")
        logger.warning(f"Page {i + 1} has low text ({text_length} chars)", extra={"api_path": "check_low_text"})
        low_text_pages.append(i)

#adding metadata to docs
for doc in documents:
    doc.metadata["source"] = "attention.pdf"
    doc.metadata["page_number"] = doc.metadata.get("page", -1)

from pdf2image import convert_from_path
POPPLER_PATH = os.getenv("POPPLER_PATH")
#Saving the low text pages as png images
for idx, page_num in enumerate(low_text_pages):
    data_folder = "data"
    img_path = os.path.join(data_folder, f"page_{page_num+1}.png")
    if not os.path.exists(img_path):
        image = convert_from_path(pdf_path, dpi=300, poppler_path=POPPLER_PATH, first_page=page_num+1, last_page=page_num+2)[0]
        image.save(img_path, "PNG") #Saves the image as a PNG file named "page_num+1.png" in the current directory.
        logger.info(f"Saved page {page_num+1} as image", extra={"api_path": "convert_to_image"})
        #print(f"Saved page {page_num+1} as image")
    else:
        logger.info(f"Image for page {page_num+1} already exists, skipping save.", extra={"api_path": "convert_to_image"})
    

import pytesseract
from PIL import Image
TESSERACT_PATH = os.getenv("TESSERACT_PATH")

#manual configuration
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


import json
#checks to see if the ocr_text exists from before
ocr_json_path = f"{os.path.splitext(pdf_path)[0]}_ocr_texts.json" #file name based on the PDF name
if os.path.exists(ocr_json_path):
    print(f"{ocr_json_path} already exists!")
    with open(ocr_json_path, 'r') as f:
        ocr_texts = json.load(f)

else:
    #text extracted from low text page imgs with ocr
    ocr_texts = []

    for page_num in low_text_pages:
        data_folder = "data"
        img_path = os.path.join(data_folder, f"page_{page_num+1}.png") #saves it in the data folder
        #img_path = f"page_{page_num+1}.png"
        img = Image.open(img_path)
        text = pytesseract.image_to_string(img)
        logger.info(f"OCR text from page {page_num+1}: {len(text)} chars", extra={"api_path": "OCR"})
        #print(f"OCR text from page {page_num+1}: {len(text)} chars")
        ocr_texts.append({
            "page": page_num,
            "text": text
        })    
    with open(ocr_json_path,"w") as f:
        json.dump(ocr_texts, f)
        print(f"created {ocr_json_path}!")
    
    

#creating docs from the extracted texts with ocr
from langchain_core.documents import Document

ocr_documents = []

for item in ocr_texts:
    page_number = item["page"]
    text = item["text"].strip()
    
    
    if len(text) > 100: #To  delete short texts or low quality images
        doc = Document(
            page_content=text,
            metadata={
                "source": pdf_path,
                "page": page_number,
                "page_number": page_number
            }
        )
        ocr_documents.append(doc)
        logger.info(f"OCR Document created for page {page_number+1}", extra={"api_path": "OCR"})
    else:
        print(f"Skipped page {page_number+1} due to short OCR text")


#removing low-text pages from original documents
filtered_documents = [doc for i, doc in enumerate(documents) if i not in low_text_pages]

#Combining filtered documents with OCR documents
final_documents = filtered_documents + ocr_documents

# clean  documents
for doc in final_documents:
    doc.page_content = clean_text(doc.page_content)
    
#Sort the final documents by page number
final_documents.sort(key=lambda doc: doc.metadata["page_number"])

print(f"Total final documents after merging: {len(final_documents)}")


from langchain.text_splitter import RecursiveCharacterTextSplitter

#splitting into chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", ".", " ", ""]
)

split_docs = text_splitter.split_documents(final_documents)

print(f"Total chunks: {len(split_docs)}")
#print(split_docs[0].page_content[:300]) it worked.
#print("meta:",split_docs[50].metadata)


from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory

import uuid

from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
#from langchain_postgres import PostgresChatMessageHistory
from langchain_community.chat_message_histories import PostgresChatMessageHistory
from langchain_postgres import PostgresChatMessageHistory
import psycopg

#memory
session_id = str(uuid.uuid4())

memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)



from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)


from langchain_postgres import PGVector

# See docker command above to launch a postgres instance with pgvector enabled.
connection = "postgresql+psycopg://langchain:langchain@localhost:6024/langchain"  # Uses psycopg3
collection_name = "my_docs"

vectorstore = PGVector(
    embeddings=embeddings,
    collection_name=collection_name,
    connection=connection,
    use_jsonb=True,
)
vectorstore.add_documents(split_docs)
print("PG vectorestore was created!")

#retrieve
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

from langchain_openai import ChatOpenAI


#chat model
chat = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, openai_api_key=OPENAI_API_KEY)

# creating a q&a chain
from langchain.chains import ConversationalRetrievalChain

qa_chain = ConversationalRetrievalChain.from_llm(llm=chat, chain_type="stuff", retriever=retriever, memory=memory)