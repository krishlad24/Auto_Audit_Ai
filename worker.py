import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
import json
import redis
import requests
import chromadb
from chromadb.utils import embedding_functions
from unidiff import PatchSet
import tree_sitter_python as tspython
from tree_sitter import Language, Parser, Query
from tree_sitter import QueryCursor
from google import genai
from google.genai import types
from chromadb.utils import embedding_functions

# --- CONFIGURATION & CLIENT INITIALIZATION ---

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
r = redis.Redis.from_url(REDIS_URL, socket_timeout=None, socket_connect_timeout=5, retry_on_timeout=True)
QUEUE_NAME = "github_tasks"

# Tree-sitter setup
PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)
# 1. AST chunking query (Functions & Classes)
CODE_QUERY = Query(PY_LANGUAGE, """
    (function_definition) @func
    (class_definition) @class
""")
# 2. Dependency tracking query (Imports & Calls)
IMPORT_QUERY = Query(PY_LANGUAGE, """
    (import_from_statement 
        module_name: (dotted_name) @from_module
        name: (dotted_name) @imported_name)
    (import_statement 
        name: (dotted_name) @direct_import)
""")

# Vector DB setup
chroma_client = chromadb.Client()
emb_fn = embedding_functions.GoogleGenAiEmbeddingFunction(
    api_key=os.getenv("GEMINI_API_KEY")
)


def extract_file_dependencies(code: str, filename: str):
    """Extracts imported modules, functions, and definitions from a file."""
    if not isinstance(code, str):
        return []

    tree = parser.parse(bytes(code, "utf8"))
    dependencies = []
    
    # 1. Capture imports
    cursor = QueryCursor(IMPORT_QUERY)

    matches = cursor.matches(tree.root_node)
    for pattern_idx, captures_dict in matches:
        for tag, nodes in captures_dict.items():
            for node in nodes:
                dep_name = code.encode("utf8")[node.start_byte:node.end_byte].decode("utf8")
                dependencies.append({
                    "type": str(tag),
                    "name": dep_name,
                    "file": filename
                })
                
    return dependencies

# --- GITHUB FETCHER ---

def fetch_diff_and_files(repo_full_name: str, base: str, head: str):
    """Fetches raw unified diff and modified file contents from GitHub."""
    diff_headers = {**HEADERS, "Accept": "application/vnd.github.v3.diff"}
    diff_url = f"https://api.github.com/repos/{repo_full_name}/compare/{base}...{head}"
    
    diff_response = requests.get(diff_url, headers=diff_headers)
    diff_text = diff_response.text

    json_response = requests.get(diff_url, headers=HEADERS).json()
    files_data = {}

    for file_meta in json_response.get("files", []):
        filename = file_meta["filename"]
        raw_url = file_meta.get("raw_url")

        # Only pull Python files for AST parsing
        if raw_url and filename.endswith(".py"):
            file_content = requests.get(raw_url, headers=HEADERS).text
            files_data[filename] = file_content

    return diff_text, files_data

ai_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
MODEL_ID = "gemini-2.5-flash"

def run_agent(system_instruction: str, user_prompt: str) -> str:
    """Executes a single focused agent role."""
    response = ai_client.models.generate_content(
        model=MODEL_ID,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2,
        )
    )
    return response.text or ""

def multi_agent_review(diff: str, ast_context: list, full_repo_files: dict):
    # 1. Build Cross-File Dependency Map
    repo_graph = {}
    for fname, content in full_repo_files.items():
        if isinstance(content, str):
            repo_graph[fname] = extract_file_dependencies(content, fname)
        
    context_blocks = []
    for c in ast_context:
        if isinstance(c, dict):
            fname = c.get("filename", "unknown")
            sline = c.get("start_line", 1)
            eline = c.get("end_line", "")
            body = c.get("content", "")
            context_blocks.append(f"// File: {fname} (L{sline}-{eline})\n{body}")
        elif isinstance(c, str):
            context_blocks.append(c)

    formatted_context = "\n\n".join(context_blocks)

    # 2. Agent 1: Code Logic & Performance
    prompt_logic = f"Context:\n{formatted_context}\n\nDiff:\n{diff}"
    sys_logic = "You are a Senior Python Engineer. Review the diff for algorithmic errors, edge cases, type issues, and performance bottlenecks."
    logic_findings = run_agent(sys_logic, prompt_logic)

    # 3. Agent 2: Security & Vulnerability Auditor
    prompt_sec = f"Diff to inspect:\n{diff}"
    sys_sec = "You are an AppSec Engineer. Flag security flaws, leaked credentials, injection vectors, and unsafe calls. If none, state 'No security issues'."
    security_findings = run_agent(sys_sec, prompt_sec)

    # 4. Agent 3: Cross-File Dependency Sentinel
    prompt_deps = f"""Repository Import Map:
{json.dumps(repo_graph, indent=2)}

Retrieved Related Chunks:
{formatted_context}

Diff Being Introduced:
{diff}"""
    sys_deps = """You are a Software Architect specializing in dependency trees. 
Determine if signature changes, renamed variables, or modified imports in this diff break any calling functions across other files in the project."""
    dependency_findings = run_agent(sys_deps, prompt_deps)

    # 5. Lead Synthesizer Agent: Final Consolidation
    synthesis_prompt = f"""Synthesize the following 3 agent reports into a unified, high-value GitHub Pull Request Review:

[Logic & Bugs Findings]:
{logic_findings}

[Security Findings]:
{security_findings}

[Cross-File Dependency Impact]:
{dependency_findings}

Format using markdown headings:
- 🚨 Critical Issues (Bugs, Security, Broken Imports)
- ⚠️ Suggestions & Optimizations
- 🔍 Cross-File Impact Summary
- Verdict: [APPROVE / COMMENT / REQUEST_CHANGES]"""

    sys_synthesizer = "You are the Lead Code Reviewer. Consolidate sub-agent inputs into a concise, professional GitHub PR comment."
    final_review = run_agent(sys_synthesizer, synthesis_prompt)

    return final_review


def post_pr_comment(repo_name: str, pr_number: str, comment_body: str):
    """Posts the generated review back to GitHub PR discussion."""
    url = f"https://api.github.com/repos/{repo_name}/issues/{pr_number}/comments"
    resp = requests.post(url, headers=HEADERS, json={"body": comment_body})
    if resp.status_code == 201:
        print(f"[+] Successfully posted review to PR #{pr_number}")
    else:
        print(f"[!] Failed to post comment: {resp.status_code} - {resp.text}")


# --- TREE-SITTER PARSING ---

def extract_ast_chunks(code: str, filename: str):
    """Parses code into functions and classes using Tree-sitter."""
    tree = parser.parse(bytes(code, "utf8"))
    chunks = []
    
    cursor = QueryCursor(CODE_QUERY)

    matches = cursor.matches(tree.root_node)
    
    for pattern_index, capture_dict in matches:
        for capture_name, nodes in capture_dict.items():
            for node in nodes:
                node_bytes = code.encode("utf8")[node.start_byte:node.end_byte]
                chunks.append({
                    "content": node_bytes.decode("utf8"),
                    "filename": filename,
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "type": node.type
                })

    if not chunks:
        chunks.append({
            "content": code,
            "filename": filename,
            "start_line": 1,
            "end_line": len(code.splitlines()),
            "type": "file"
        })
        
    return chunks


# --- VECTOR DATABASE & DIFF RAG ---

def store_chunks_in_vectordb(collection, chunks):
    """Indexes AST chunks into the active temporary collection."""
    if not chunks:
        return
    documents = [c["content"] for c in chunks]
    metadatas = [{
        "filename": c["filename"],
        "start_line": c["start_line"],
        "end_line": c["end_line"],
        "type": c["type"]
    } for c in chunks]
    ids = [f"{c['filename']}:{c['start_line']}-{c['end_line']}" for c in chunks]

    collection.upsert(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

def extract_added_diff_context(git_diff_str: str) -> str:
    """Parses unified diff and extracts only added/modified lines for search."""
    try:
        patch = PatchSet(git_diff_str)
        search_terms = []
        for patched_file in patch:
            for hunk in patched_file:
                added_lines = [line.value.strip() for line in hunk if line.is_added]
                search_terms.extend(added_lines)
        return " \n ".join(search_terms)
    except Exception:
        # Fallback if raw diff is not standard patch
        return git_diff_str

def retrieve_diff_context(collection, git_diff_str: str, top_k: int = 3):
    """Queries Vector DB using the Git diff as the retrieval prompt."""
    query_text = extract_added_diff_context(git_diff_str)
    
    if not query_text.strip() or collection.count() == 0:
        return None

    results = collection.query(
        query_texts=[query_text],
        n_results=min(top_k, collection.count())
    )
    return results


# --- MAIN WORKER PIPELINE ---

def process_worker():
    print("Worker ready and waiting for jobs...")
    while True:
        try:
            job = r.blpop(QUEUE_NAME, timeout=2)
            if not job:
                continue

            _, data = job
            task = json.loads(data)
            payload = task.get("payload", {})
            repo_name = payload.get("repository")
            if isinstance(repo_name, dict):
                repo_name = repo_name.get("full_name")

            before_sha = payload.get("before") or payload.get("base_sha") or "main"
            after_sha = payload.get("after") or payload.get("commit_sha")

            if not (repo_name and after_sha):
                print(f"[!] Skipped task - missing required fields: {payload}")
                continue
            # Handle GitHub push events
                
            # Temporary collection ID for this commit cycle
            collection_name = f"rev_{after_sha[:8]}"
            print(f"\n[+] Starting review cycle for {repo_name} ({before_sha[:7]}..{after_sha[:7]})")

            # 1. Create temporary collection
            temp_collection = chroma_client.create_collection(
                name=collection_name, 
                embedding_function=emb_fn  # type: ignore
            )

            try:
                # 2. Fetch diff & code files
                diff, full_files = fetch_diff_and_files(repo_name, before_sha, after_sha)
                print(f"    - Fetched {len(full_files)} Python file(s), diff size: {len(diff)} bytes")

                # 3. Parse AST chunks & populate collection
                for filename, code in full_files.items():
                    chunks = extract_ast_chunks(code, filename)
                    store_chunks_in_vectordb(temp_collection, chunks)
                print(f"    - Indexed {temp_collection.count()} AST code chunks")

                # 4. RAG Retrieval via Git Diff
                rag_results = retrieve_diff_context(temp_collection, diff, top_k=3)

                
                print("    - Top relevant code chunks retrieved for diff:")
                retrieved_chunks = []
                if rag_results:
                    raw_docs = rag_results.get("documents")
                    raw_metas = rag_results.get("metadatas")

                    if raw_docs and raw_metas and len(raw_docs) > 0:
                        for doc, meta in zip(raw_docs[0], raw_metas[0]):
                            if isinstance(meta, dict):
                                retrieved_chunks.append(f"      * [{meta.get('filename')}:{meta.get('start_line')}] {meta.get('type')}")
                
                # 5. Run Multi-Agent Code Review
                print(f"[+] Running multi-agent review with {len(retrieved_chunks)} context chunk(s)...")
                final_review = multi_agent_review(
                    diff=diff,
                    ast_context=retrieved_chunks,
                    full_repo_files=full_files
                )

                # 6. Post the generated review directly to the GitHub PR
                pr_number = payload.get("pr_number")
                if pr_number:
                    post_pr_comment(repo_name, str(pr_number), final_review)
                else:
                    print("[!] No pr_number found in payload; skipping GitHub comment post.")
                

            finally:
                # 6. Purge vector data after review cycle
                chroma_client.delete_collection(name=collection_name)
                print(f"[x] Cleaned up and deleted collection: {collection_name}")
        except redis.exceptions.TimeoutError:
            # Handles socket hiccups gracefully without crashing the loop
            continue
        except redis.exceptions.ConnectionError:
            print("Lost connection to Redis, retrying in 2 seconds...")
            import time
            time.sleep(2)
            continue
        except Exception as e:
            print(f"Error processing job: {e}")

if __name__ == "__main__":
    process_worker()
