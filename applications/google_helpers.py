from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request

import os 
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
import re

load_dotenv()

CREDS_FILE = os.getenv("GOOGLE_CREDENTIALS_JSON")
SCOPES = [s.strip() for s in os.getenv("GOOGLE_SCOPES", "").split(",") if s.strip()]
DELEGATED_USER = os.getenv("GOOGLE_WORKSPACE_DELEGATED_USER")
print(DELEGATED_USER)
# --- Google auth/services ---
def get_creds():
    if not CREDS_FILE:
        raise RuntimeError("GOOGLE_CREDENTIALS_JSON not set")
    creds = service_account.Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    print("Scope", creds._scopes)
    if DELEGATED_USER:
        creds = creds.with_subject(DELEGATED_USER)
    creds.refresh(Request())
    print("token ok, expires:", creds.expiry)
    return creds

def drive_svc():
    return build("drive", "v3", credentials=get_creds(), cache_discovery=False)

def docs_svc():
    return build("docs", "v1", credentials=get_creds(), cache_discovery=False)

# --- URL → fileId ---
DOC_URL_RE = re.compile(r"docs\.google\.com/document/d/([a-zA-Z0-9-_]+)")

def extract_file_id(url: str) -> str:
    m = DOC_URL_RE.search(url)
    if not m:
        raise ValueError("Could not parse Google Doc fileId from URL.")
    return m.group(1)

# --- Docs parsing ---
def fetch_doc(document_id: str) -> Dict[str, Any]:
    return docs_svc().documents().get(documentId=document_id).execute()

def flatten_paragraphs(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for c in doc.get("body", {}).get("content", []):
        para = c.get("paragraph")
        if not para: 
            continue
        buf, start, end = [], None, None
        for e in para.get("elements", []):
            tr = e.get("textRun")
            if not tr: 
                continue
            t = tr.get("content")
            if t:
                buf.append(t)
                start = e.get("startIndex") if start is None else start
                end = e.get("endIndex")
        text = "".join(buf).strip()
        if text:
            out.append({"text": text, "start": start, "end": end})
    return out

def post_file_comment(file_id: str, content: str, quoted: Optional[str] = None):
    body: Dict[str, Any] = {"content": content}
    if quoted:
        body["quotedFileContent"] = {"value": quoted, "mimeType": "text/plain"}
    return drive_svc().comments().create(fileId=file_id, body=body).execute()

def allowed(file_id: str) -> bool:
    return not ALLOW_FILE_IDS or file_id in ALLOW_FILE_IDS

def dedupe_key(file_id: str, suggestion: str) -> str:
    import hashlib
    return hashlib.sha256(f"{file_id}|{suggestion}".encode()).hexdigest()


if __name__ == "__main__":
    ALLOW_FILE_IDS = set()   # fill with allowed files or leave empty to allow all
    MAX_COMMENTS_PER_FILE_PER_DAY = 5
    DEDUP = set()            # swap for Redis/DB in prod



    doc_url = "https://docs.google.com/document/d/1czGLOuVLVFIkp1Wr4N11nzgxtNuaBNQgA_gRMfQS9V4/edit?usp=sharing"
    suggestion = "test"
    quoted = None
    
    file_id = extract_file_id(doc_url)
    
    res = post_file_comment(file_id, content=suggestion, quoted=quoted)
    print(res)

