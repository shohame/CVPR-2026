import logging
import sys
import warnings
import os
from io import StringIO
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

# Add parent directory to path so we can import Semantic_Search_V2
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Set environment variables to suppress warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['PYTHONWARNINGS'] = 'ignore'
os.environ['STREAMLIT_LOGGER_LEVEL'] = 'critical'

# Suppress all warnings
warnings.filterwarnings('ignore')

# Configure logging before any imports
logging.basicConfig(level=logging.CRITICAL, force=True)

# Pre-configure Streamlit logger
streamlit_logger = logging.getLogger("streamlit")
streamlit_logger.setLevel(logging.CRITICAL)
streamlit_logger.propagate = False

script_run_logger = logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context")
script_run_logger.setLevel(logging.CRITICAL)
script_run_logger.propagate = False

# Create a filter to suppress the specific warning
class SupressScriptRunContextWarning(logging.Filter):
    def filter(self, record):
        if "missing ScriptRunContext" in record.getMessage():
            return False
        return True

# Apply the filter
script_run_logger.addFilter(SupressScriptRunContextWarning())

# Suppress logs for these modules
for logger_name in ["streamlit", "urllib3", "torch"]:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.CRITICAL)
    logger.propagate = False

import streamlit as st
from Semantic_Search_V2.Run_Semantic_Search import Run_Semantic_Search

# Set page config
st.set_page_config(page_title="CVPR 2026 Search Engine", layout="wide")


# Initialize the search engine (cached to avoid reloading model on every interaction)
@st.cache_resource
def get_searcher():
    # Redirect stderr to suppress any warnings during initialization
    old_stderr = sys.stderr
    sys.stderr = StringIO()
    try:
        searcher = Run_Semantic_Search()
        return searcher
    finally:
        sys.stderr = old_stderr


@st.cache_data(show_spinner=False)
def load_pdf_bytes_from_disk(pdf_path: str):
    if not os.path.exists(pdf_path):
        return None
    with open(pdf_path, "rb") as f:
        return f.read()


@st.cache_data(show_spinner=False)
def load_pdf_bytes_from_url(pdf_url: str):
    with urlopen(pdf_url, timeout=20) as resp:
        return resp.read()


searcher = get_searcher()

st.title("🔍 CVPR 2026 Semantic Search")
st.markdown(
    "Search for papers using natural language. Expand a title to read the **Abstract**, then download the **PDF** directly.")

# Search input
query = st.text_input("Enter your research topic:", placeholder="e.g., Unsupervised domain adaptation for drones")

if query:
    indices = searcher.get_semantic_search_top_indices(query, top_k=10)

    # Display results
    for rank, idx in enumerate(indices, start=1):
        paper_prop = searcher.get_paper_properties(idx)
        title = paper_prop.get('paper_name', 'Unknown Title').replace("_", " ")
        # Use an expander for the abstract
        with st.expander(f"{rank}. {title}"):
            abstract = searcher.read_abstract(idx)
            st.write("**Abstract:**")
            st.write(abstract)

            # PDF delivery logic (send file bytes instead of opening local path)
            pdf_path = paper_prop['download_paths']['pdf']
            pdf_url = paper_prop['urls']['pdf']
            pdf_filename = f"{title}.pdf".replace("/", "-").replace("\\", "-")

            pdf_bytes = load_pdf_bytes_from_disk(pdf_path)
            if pdf_bytes is not None:
                st.download_button(
                    label="Download PDF",
                    data=pdf_bytes,
                    file_name=pdf_filename,
                    mime="application/pdf",
                    key=f"download_local_{idx}",
                )
            else:
                try:
                    pdf_bytes = load_pdf_bytes_from_url(pdf_url)
                    st.download_button(
                        label="Download PDF",
                        data=pdf_bytes,
                        file_name=pdf_filename,
                        mime="application/pdf",
                        key=f"download_remote_{idx}",
                    )
                except URLError:
                    st.error("Could not fetch the PDF file right now.")
                    st.link_button("Open official PDF page", pdf_url)

st.sidebar.markdown("### Instructions")
st.sidebar.info(
    "1. Type a query in the box.\n2. Click a title to expand and read the abstract.\n3. Click **Download PDF** to receive the file.")
