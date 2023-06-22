from langchain.chains import RetrievalQA
# from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceInstructEmbeddings
from langchain.llms import HuggingFacePipeline, BaseLLM
from langchain.prompts import PromptTemplate
from constants import CHROMA_SETTINGS, PERSIST_DIRECTORY

import gradio as gr
import torch
from transformers import pipeline, AutoModelForCausalLM
from run_localGPT import load_ko_alpaca, load_openai_model, load_kullm_model

import os
from dotenv import load_dotenv
from fastapi import FastAPI
from langchain import ConversationChain
from langchain.chat_models import ChatOpenAI

from lanarky import LangchainRouter


def answer(state, state_chatbot, text):

    # Interactive questions and answers

    query = input("\n질문을 입력하세요: ")

    # Get the answer from the chain
    res = qa({"query": query})
    answer, docs = res['result'], res['source_documents']

    # Print the result
    print("\n\n> 질문:")
    print(query)
    print("\n> 대답:")
    print(answer)

    # # Print the relevant sources used for the answer
    print("----------------------------------참조한 문서---------------------------")
    for document in docs:
        print("\n> " + document.metadata["source"] + ":")
        print(document.page_content)
    print("----------------------------------참조한 문서---------------------------")

    return state, state_chatbot, state_chatbot

device = "cpu"
model_type = "koAlpaca"
os.environ["OPENAI_API_KEY"] = "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"
llm = load_openai_model()
with gr.Blocks(css="#chatbot .overflow-y-auto{height:750px}") as demo:
    with gr.Tab("Setting"):
        device_type = gr.Textbox("Device Type (CPU, GPU, MPS 중 택1)")
        if device_type in ['cpu', 'CPU']:
            device = 'cpu'
        elif device_type in ['mps', 'MPS']:
            device = 'mps'
        elif device_type in ['gpu', 'GPU']:
            device = 'cuda'
        else:
            #raise ValueError(f"Invalid device type: {device_type}")
            gr.Error(f"Invalid device type: {device_type}")

        #model_type = gr.Textbox("Model (KoAlpaca, KuLLM, OpenAI 중 택1)")
        #openai_token = gr.Textbox("OpenAI 토큰")
        #if model_type in ['koAlpaca', 'KoAlpaca', 'koalpaca', 'Ko-alpaca']:
        #    llm = load_ko_alpaca(device)
        #elif model_type in ["OpenAI", "openai", "Openai"]:
        #    os.environ["OPENAI_API_KEY"] = openai_token
        #    llm = load_openai_model()
        #elif model_type in ["KULLM", "KuLLM", "kullm"]:
        #    llm = load_kullm_model(device)
        #else:
        #    #raise ValueError(f"Invalid model type: {model_type}")
        #    gr.Error(f"Invalid model type: {model_type}")
        #gr.Markdown(f"Running on: {device} Running with: {model_type}")

    embeddings = HuggingFaceInstructEmbeddings(model_name="BM-K/KoSimCSE-roberta-multitask",
                                               model_kwargs={"device": device})
    # load the vectorstore
    db = Chroma(persist_directory=PERSIST_DIRECTORY, embedding_function=embeddings, client_settings=CHROMA_SETTINGS)
    retriever = db.as_retriever()
    # Prepare the LLM
    # callbacks = [StreamingStdOutCallbackHandler()]
    # load the LLM for generating Natural Language responses.
    prompt_template = """주어진 정보를 바탕으로 질문에 답하세요. 답을 모른다면 답을 지어내려고 하지 말고 모른다고 답하세요. 
    질문 이외의 상관 없는 답변을 하지 마세요. 반드시 한국어로 답변하세요.

    {context}

    질문: {question}
    한국어 답변:"""
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain_type_kwargs = {"prompt": prompt}
    qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever, return_source_documents=True,
                                     chain_type_kwargs=chain_type_kwargs)

    state = gr.State(
        [
            {
                "role": "맥락",
                "content": "KoAlpaca(코알파카)는 EleutherAI에서 개발한 Polyglot-ko 라는 한국어 모델을 기반으로, 자연어 처리 연구자 Beomi가 개발한 모델입니다.",
            },
            {
                "role": "맥락",
                "content": "ChatKoAlpaca(챗코알파카)는 KoAlpaca를 채팅형으로 만든 것입니다.",
            },
            {"role": "명령어", "content": "친절한 AI 챗봇인 ChatKoAlpaca 로서 답변을 합니다."},
            {
                "role": "명령어",
                "content": "인사에는 짧고 간단한 친절한 인사로 답하고, 아래 대화에 간단하고 짧게 답해주세요.",
            },
        ]
    )
    state_chatbot = gr.State([])
    with gr.Tab("Setting"):
        with gr.Row():
            gr.HTML(
                """<div style="text-align: center; max-width: 500px; margin: 0 auto;">
                <div>
                    <h1>ChatKoAlpaca 12.8B (v1.1b-chat-8bit)</h1>
                </div>
                <div>
                    Demo runs on RTX 3090 (24GB) with 8bit quantized
                </div>
            </div>"""
            )

        with gr.Row():
            chatbot = gr.Chatbot(elem_id="chatbot")

        with gr.Row():
            txt = gr.Textbox(show_label=False, placeholder="Send a message...").style(
                container=False
            )

        txt.submit(answer, [state, state_chatbot, txt], [state, state_chatbot, chatbot])
        txt.submit(lambda: "", None, txt)

demo.launch(share=True, debug=True, server_name="0.0.0.0")
