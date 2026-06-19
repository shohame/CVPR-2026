import logging
import sys
import warnings
import os
from io import StringIO
from pathlib import Path
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote, quote

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
    if not pdf_path or not os.path.exists(pdf_path):
        return None
    with open(pdf_path, "rb") as f:
        return f.read()


def _is_path_within_root(file_path: Path, root_path: Path):
    try:
        file_path.resolve().relative_to(root_path.resolve())
        return True
    except ValueError:
        return False


def _build_pdf_handler(root_dir: Path):
    class LocalPdfHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path != "/pdf":
                self.send_error(404, "Not Found")
                return

            query = parse_qs(parsed.query)
            raw_path = query.get("path", [None])[0]
            if not raw_path:
                self.send_error(400, "Missing path")
                return

            requested = Path(unquote(raw_path))
            if not requested.exists() or not requested.is_file():
                self.send_error(404, "PDF not found")
                return

            if not _is_path_within_root(requested, root_dir):
                self.send_error(403, "Access denied")
                return

            try:
                with open(requested, "rb") as pdf_file:
                    data = pdf_file.read()
            except OSError:
                self.send_error(500, "Unable to read PDF")
                return

            filename = requested.name.replace('"', "")
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", f'inline; filename="{filename}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format, *args):
            return

    return LocalPdfHandler


@st.cache_resource
def start_local_pdf_server(root_dir: str):
    root_path = Path(root_dir).resolve()
    handler_cls = _build_pdf_handler(root_path)
    server = ThreadingHTTPServer(("0.0.0.0", 8765), handler_cls)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return {"port": 8765, "root": str(root_path)}


def get_request_hostname(default_host: str = "localhost"):
    try:
        host_header = st.context.headers.get("host", "")
    except Exception:
        host_header = ""

    if host_header:
        return host_header.split(":")[0]
    return default_host


searcher = get_searcher()
pdf_server = start_local_pdf_server(str(Path(__file__).parent.parent))
pdf_host = get_request_hostname()
pdf_port = pdf_server["port"]

st.title("🔍 CVPR 2026 Semantic Search")
st.markdown(
    "Search for papers using natural language. Expand a title to read the **Abstract**, then open the **PDF** in a new browser tab.")

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

            # Server reads local PDF from disk and sends it to the browser for viewing.
            pdf_path = paper_prop['download_paths']['pdf']
            if pdf_path and os.path.exists(pdf_path):
                encoded_path = quote(str(Path(pdf_path).resolve()), safe="")
                pdf_link = f"http://{pdf_host}:{pdf_port}/pdf?path={encoded_path}"
                st.markdown(
                    f'<a href="{pdf_link}" target="_blank" rel="noopener noreferrer">Open PDF in New Tab</a>',
                    unsafe_allow_html=True,
                )
            else:
                st.error("Local PDF file is missing for this paper.")

st.sidebar.markdown("### Instructions")
st.sidebar.info(
    "1. Type a query in the box.\n2. Click a title to expand and read the abstract.\n3. Click **Open PDF in New Tab** to view it; save from the browser if needed.")
