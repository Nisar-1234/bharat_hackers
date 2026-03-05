"""Streamlit UI for Jansahayak - GenAI Citizen Assistant."""
import streamlit as st
import requests
import os
from pathlib import Path
import json
from datetime import datetime
from audio_recorder_streamlit import audio_recorder

# Page configuration
st.set_page_config(
    page_title="Jansahayak - जनसहायक",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load API endpoint from environment
API_ENDPOINT = os.getenv("API_ENDPOINT", "http://localhost:8000")

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #FF9933;
        text-align: center;
        padding: 1rem;
        background: linear-gradient(90deg, #FF9933 0%, #FFFFFF 50%, #138808 100%);
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #138808;
        color: white;
        font-weight: bold;
    }
    .citation-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #FF9933;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #28a745;
    }
    .error-box {
        background-color: #f8d7da;
        padding: 1rem;
        border-radius: 5px;
        border-left: 4px solid #dc3545;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header"> Jansahayak - जनसहायक</h1>', unsafe_allow_html=True)
st.markdown("### GenAI-Powered Citizen Assistant for Government Schemes")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Flag_of_India.svg/320px-Flag_of_India.svg.png", width=100)
    st.title("Navigation")

    pages = [" Home", " Upload Document", " Text Query", " Voice Query", " Document Library"]
    # Honour navigation from Home page buttons
    default_index = 0
    if "page" in st.session_state and st.session_state.page in pages:
        default_index = pages.index(st.session_state.page)

    page = st.radio(
        "Select a feature:",
        pages,
        index=default_index,
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("### About")
    st.info("""
    **Jansahayak** helps rural citizens understand government welfare schemes through:
    -  Document processing (OCR)
    -  Text queries with citations
    -  Voice queries in regional languages
    -  Hindi, Telugu, Tamil, English support
    """)
    
    st.markdown("---")
    st.markdown("### API Status")
    try:
        response = requests.get(f"{API_ENDPOINT}/", timeout=5)
        if response.status_code == 200:
            st.success(" API Connected")
        else:
            st.error(" API Error")
    except:
        st.error(" API Offline")
    
    st.markdown(f"**Endpoint:** `{API_ENDPOINT}`")

# Main content area
if page == " Home":
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("###  Document Processing")
        st.write("Upload government scheme PDFs and images. Our OCR extracts text and creates a searchable knowledge base.")
        if st.button("Upload Document →", key="home_upload"):
            st.session_state.page = " Upload Document"
            st.rerun()
    
    with col2:
        st.markdown("###  Text Queries")
        st.write("Ask questions about schemes in your language. Get accurate answers with source citations.")
        if st.button("Ask Question →", key="home_query"):
            st.session_state.page = " Text Query"
            st.rerun()
    
    with col3:
        st.markdown("###  Voice Queries")
        st.write("Speak your question in Hindi, Telugu, Tamil, or English. Get voice responses back.")
        if st.button("Voice Query →", key="home_voice"):
            st.session_state.page = " Voice Query"
            st.rerun()
    
    st.markdown("---")
    st.markdown("###  Key Features")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        -  **OCR Processing**: Extract text from PDFs and images
        -  **Semantic Search**: Understand intent, not just keywords
        -  **Fact-Checked**: Every answer includes source citations
        """)
    
    with col2:
        st.markdown("""
        -  **Multilingual**: Hindi, Telugu, Tamil, English
        -  **Voice-First**: Accessible to low-literacy users
        -  **Fast**: Sub-10 second response time
        """)

elif page == " Upload Document":
    st.header(" Upload Government Scheme Document")
    st.markdown("Upload PDF or image files (max 50MB). The system will extract text and make it searchable.")
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "png", "jpg", "jpeg"],
        help="Supported formats: PDF, PNG, JPG, JPEG (max 50MB)"
    )
    
    if uploaded_file is not None:
        st.info(f"**File:** {uploaded_file.name} ({uploaded_file.size / 1024 / 1024:.2f} MB)")
        
        if st.button(" Upload and Process", type="primary"):
            if uploaded_file.size > 50 * 1024 * 1024:
                st.error(" File size exceeds 50MB limit")
            else:
                with st.spinner("Uploading and processing document... This may take a few minutes."):
                    try:
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        response = requests.post(f"{API_ENDPOINT}/documents/upload", files=files, timeout=300)
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.markdown(f'<div class="success-box"> <b>Document uploaded successfully!</b><br>Document ID: {result.get("document_id")}<br>Status: {result.get("status")}</div>', unsafe_allow_html=True)
                            
                            st.info(" Processing started. Check 'Document Library' to see status.")
                        else:
                            error_data = response.json()
                            st.markdown(f'<div class="error-box"> <b>Upload failed:</b> {error_data.get("message", "Unknown error")}</div>', unsafe_allow_html=True)
                    except requests.exceptions.Timeout:
                        st.error("⏱ Request timed out. The document may still be processing. Check Document Library.")
                    except Exception as e:
                        st.error(f" Error: {str(e)}")

elif page == " Text Query":
    st.header(" Ask a Question")
    st.markdown("Ask questions about government schemes. Get accurate answers with source citations.")

    # Language selection
    language_map = {
        "English": "en",
        "हिंदी (Hindi)": "hi",
        "తెలుగు (Telugu)": "te",
        "தமிழ் (Tamil)": "ta"
    }

    selected_language = st.selectbox(
        "Select Language",
        options=list(language_map.keys()),
        index=0
    )

    language_code = language_map[selected_language]

    # Sample questions — click to prefill
    st.markdown("**Try a sample question:**")
    sample_questions = [
        "What is the eligibility criteria for PM-KISAN scheme?",
        "What are the benefits under Ayushman Bharat health insurance?",
        "Who is eligible for PM Ujjwala Yojana free LPG connection?",
        "What documents are required to apply for the scheme?",
        "How much financial assistance is provided under PM Awas Yojana?",
    ]

    if "prefill_query" not in st.session_state:
        st.session_state.prefill_query = ""

    cols = st.columns(len(sample_questions))
    for i, (col, q) in enumerate(zip(cols, sample_questions)):
        with col:
            short_label = q[:30] + "…" if len(q) > 30 else q
            if st.button(short_label, key=f"sample_{i}"):
                st.session_state.prefill_query = q

    # Query input
    query_text = st.text_area(
        "Your Question",
        value=st.session_state.prefill_query,
        placeholder="Example: What is the eligibility criteria for PM-KISAN scheme?",
        height=100,
        key="query_input",
    )
    
    if st.button(" Get Answer", type="primary"):
        if not query_text.strip():
            st.warning(" Please enter a question")
        else:
            with st.spinner("Searching knowledge base and generating answer..."):
                try:
                    payload = {
                        "query": query_text,
                        "language": language_code
                    }
                    response = requests.post(
                        f"{API_ENDPOINT}/query/text",
                        json=payload,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # Display answer
                        st.markdown("###  Answer")
                        st.success(result.get("answer", "No answer available"))
                        
                        # Display processing time
                        processing_time = result.get("processing_time_ms", 0)
                        st.caption(f"⏱ Processing time: {processing_time}ms")
                        
                        # Display citations
                        citations = result.get("citations", [])
                        if citations:
                            st.markdown("###  Sources & Citations")
                            for i, citation in enumerate(citations, 1):
                                st.markdown(f"""
                                <div class="citation-box">
                                    <b>Citation {i}</b><br>
                                     <b>Document:</b> {citation.get('document_name', 'N/A')}<br>
                                     <b>Page:</b> {citation.get('page_number', 'N/A')}<br>
                                     <b>Section:</b> {citation.get('clause_reference', 'N/A')}<br>
                                     <b>Excerpt:</b> "{citation.get('excerpt', 'N/A')}"<br>
                                     <b>Confidence:</b> {citation.get('confidence_score', 0):.2%}
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.info("ℹ No citations available for this query")
                    else:
                        error_data = response.json()
                        st.error(f" Query failed: {error_data.get('message', 'Unknown error')}")
                except requests.exceptions.Timeout:
                    st.error("⏱ Request timed out. Please try again.")
                except Exception as e:
                    st.error(f" Error: {str(e)}")

elif page == " Voice Query":
    st.header(" Voice Query")
    st.markdown("Speak your question or upload an audio file. Get a voice response back.")

    # Language selection
    language_map = {
        "English": "en",
        "हिंदी (Hindi)": "hi",
        "తెలుగు (Telugu)": "te",
        "தமிழ் (Tamil)": "ta"
    }

    selected_language = st.selectbox(
        "Select Language",
        options=list(language_map.keys()),
        index=0,
        key="voice_lang"
    )

    language_code = language_map[selected_language]

    # --- Two input modes: Mic or File upload ---
    input_mode = st.radio(
        "How would you like to ask?",
        ["Record with Microphone", "Upload Audio File"],
        horizontal=True,
        key="voice_input_mode",
    )

    audio_bytes = None
    audio_filename = "recording.wav"

    if input_mode == "Record with Microphone":
        st.markdown("Click the mic icon below, speak your question, then click again to stop.")
        recorded = audio_recorder(
            text="",
            recording_color="#e74c3c",
            neutral_color="#138808",
            icon_size="2x",
            pause_threshold=3.0,
            key="voice_recorder",
        )
        if recorded:
            audio_bytes = recorded
            audio_filename = "recording.wav"
            st.audio(recorded, format="audio/wav")
            st.success("Recording captured! Click 'Get Answer' to process.")
    else:
        audio_file = st.file_uploader(
            "Upload Audio File",
            type=["mp3", "wav", "flac"],
            help="Supported formats: MP3, WAV, FLAC",
        )
        if audio_file is not None:
            audio_bytes = audio_file.getvalue()
            audio_filename = audio_file.name
            st.audio(audio_bytes, format=audio_file.type or "audio/mpeg")

    # --- Process button ---
    if audio_bytes and st.button("Get Answer", type="primary"):
        with st.spinner("Processing voice query... This may take 30-60 seconds."):
            try:
                mime = "audio/wav" if audio_filename.endswith(".wav") else "audio/mpeg"
                files = {"audio": (audio_filename, audio_bytes, mime)}
                data = {"language": language_code}

                response = requests.post(
                    f"{API_ENDPOINT}/query/voice",
                    files=files,
                    data=data,
                    timeout=180,
                )

                if response.status_code == 200:
                    result = response.json()

                    # Display transcription
                    st.markdown("### Transcription")
                    st.info(result.get("transcribed_text", "N/A"))

                    # Display answer
                    st.markdown("### Answer")
                    st.success(result.get("answer_text", "No answer available"))

                    # Display audio response
                    audio_url = result.get("audio_url")
                    if audio_url:
                        st.markdown("### Voice Response")
                        try:
                            audio_resp = requests.get(audio_url, timeout=15)
                            audio_resp.raise_for_status()
                            st.audio(audio_resp.content, format="audio/mpeg")
                        except Exception:
                            st.audio(audio_url)

                    # Display citations
                    citations = result.get("citations", [])
                    if citations:
                        st.markdown("### Sources")
                        for i, citation in enumerate(citations, 1):
                            with st.expander(f"Citation {i}: {citation.get('document_name', 'N/A')}"):
                                st.write(f"**Page:** {citation.get('page_number', 'N/A')}")
                                st.write(f"**Section:** {citation.get('clause_reference', 'N/A')}")
                                st.write(f"**Excerpt:** {citation.get('excerpt', 'N/A')}")
                                st.write(f"**Confidence:** {citation.get('confidence_score', 0):.2%}")
                else:
                    error_data = response.json()
                    st.error(f"Voice query failed: {error_data.get('message', 'Unknown error')}")
            except requests.exceptions.Timeout:
                st.error("Request timed out. Voice processing can take up to 60 seconds.")
            except Exception as e:
                st.error(f"Error: {str(e)}")

elif page == " Document Library":
    st.header(" Document Library")
    st.markdown("View all uploaded documents and their processing status.")
    
    # Filters
    col1, col2 = st.columns([3, 1])
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "pending", "processing", "completed", "failed"],
            index=0
        )
    with col2:
        limit = st.number_input("Limit", min_value=5, max_value=50, value=10, step=5)
    
    if st.button(" Refresh", type="primary"):
        st.rerun()
    
    # Fetch documents
    try:
        params = {"limit": limit}
        if status_filter != "All":
            params["status"] = status_filter
        
        response = requests.get(f"{API_ENDPOINT}/documents", params=params, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            documents = result if isinstance(result, list) else result.get("documents", [])
            
            if documents:
                st.success(f" Found {len(documents)} document(s)")
                
                for doc in documents:
                    with st.expander(f" {doc.get('filename', 'Unknown')} - {doc.get('status', 'unknown').upper()}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Document ID:** `{doc.get('document_id', 'N/A')}`")
                            st.write(f"**Status:** {doc.get('status', 'N/A').upper()}")
                            st.write(f"**Upload Date:** {doc.get('upload_date', 'N/A')}")
                        
                        with col2:
                            st.write(f"**Chunks:** {doc.get('chunk_count', 0)}")
                            st.write(f"**File Size:** {doc.get('file_size_bytes', 0) / 1024 / 1024:.2f} MB")
                        
                        # Status-specific actions
                        if doc.get('status') == 'completed':
                            st.success(" Document is ready for queries")
                        elif doc.get('status') == 'processing':
                            st.info("⏳ Document is being processed...")
                        elif doc.get('status') == 'failed':
                            st.error(" Processing failed")
                        elif doc.get('status') == 'pending':
                            st.warning("⏸ Processing pending")
            else:
                st.info("ℹ No documents found. Upload a document to get started!")
        else:
            st.error(" Failed to fetch documents")
    except Exception as e:
        st.error(f" Error: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    <p> <b>Jansahayak - जनसहायक</b> | AI for Rural Innovation and Sustainable Systems</p>
    <p>Built with  for AWS GenAI Hackathon | Powered by Amazon Bedrock, Claude 3 Sonnet, and AWS AI Services</p>
</div>
""", unsafe_allow_html=True)
