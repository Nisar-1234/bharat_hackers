"""Rigorous end-to-end testing of Jansahayak API.

Runs text queries, voice queries, and document operations.
Saves every response to test_results/ folder.
"""
import requests
import json
import os
import time
import struct
import math
from datetime import datetime

API = os.getenv("API_ENDPOINT", "http://localhost:8000")
RESULTS = "test_results"

# ── helpers ──────────────────────────────────────────────────────────────────

def save(folder, name, data):
    path = os.path.join(RESULTS, folder, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def make_wav(duration_sec=3, sample_rate=16000, frequency=440):
    """Generate a valid WAV file with a sine wave tone."""
    num_samples = int(sample_rate * duration_sec)
    # WAV header
    data_size = num_samples * 2  # 16-bit mono
    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        36 + data_size,
        b'WAVE',
        b'fmt ',
        16,        # chunk size
        1,         # PCM
        1,         # mono
        sample_rate,
        sample_rate * 2,  # byte rate
        2,         # block align
        16,        # bits per sample
        b'data',
        data_size,
    )
    # Generate sine wave samples
    samples = b''
    for i in range(num_samples):
        value = int(32767 * 0.5 * math.sin(2 * math.pi * frequency * i / sample_rate))
        samples += struct.pack('<h', value)
    return header + samples


def make_silent_mp3():
    """Generate a minimal valid MP3 frame (near-silence)."""
    # MPEG1 Layer3 128kbps 44100Hz stereo frame
    header = bytes([0xFF, 0xFB, 0x90, 0x00])
    frame = header + b'\x00' * 413
    return frame * 50  # ~50 frames, about 1.3 seconds


# ── 1. Health Check ──────────────────────────────────────────────────────────

def test_health():
    log("TEST: Health check")
    r = requests.get(f"{API}/", timeout=10)
    result = {"status_code": r.status_code, "body": r.json(), "test": "health_check"}
    save("text_queries", "00_health_check", result)
    log(f"  → {r.status_code}: {r.json()}")
    return r.status_code == 200


# ── 2. Document operations ───────────────────────────────────────────────────

def test_list_documents():
    log("TEST: List all documents")
    r = requests.get(f"{API}/documents?limit=50", timeout=15)
    result = {"status_code": r.status_code, "body": r.json(), "test": "list_documents"}
    save("document_queries", "01_list_all", result)
    docs = r.json()
    log(f"  → {len(docs)} document(s) found")
    return docs


def test_list_documents_by_status(status):
    log(f"TEST: List documents with status={status}")
    r = requests.get(f"{API}/documents?status={status}&limit=50", timeout=15)
    result = {"status_code": r.status_code, "body": r.json(), "test": f"list_{status}"}
    save("document_queries", f"02_list_{status}", result)
    docs = r.json()
    log(f"  → {len(docs)} document(s)")
    return docs


def test_document_status(doc_id, doc_name):
    log(f"TEST: Get status of '{doc_name}' ({doc_id[:8]}...)")
    r = requests.get(f"{API}/documents/{doc_id}/status", timeout=15)
    result = {"status_code": r.status_code, "body": r.json(), "test": "doc_status"}
    save("document_queries", f"03_status_{doc_name}", result)
    log(f"  → {r.status_code}: status={r.json().get('status')}")


def test_document_not_found():
    log("TEST: Get status of non-existent document")
    r = requests.get(f"{API}/documents/fake-id-12345/status", timeout=15)
    result = {"status_code": r.status_code, "body": r.json(), "test": "doc_not_found"}
    save("document_queries", "04_not_found", result)
    log(f"  → {r.status_code}: {r.json()}")


# ── 3. Text queries ──────────────────────────────────────────────────────────

TEXT_QUERIES = [
    # English queries - various topics
    {"query": "What is PM-KISAN scheme?", "language": "en",
     "desc": "basic_what_is_pmkisan"},
    {"query": "Who is eligible for PM-KISAN?", "language": "en",
     "desc": "eligibility_pmkisan"},
    {"query": "How much money do farmers get under PM-KISAN?", "language": "en",
     "desc": "amount_pmkisan"},
    {"query": "How to apply for PM-KISAN scheme?", "language": "en",
     "desc": "how_to_apply"},
    {"query": "What documents are required for PM-KISAN?", "language": "en",
     "desc": "required_documents"},
    {"query": "What is the National Pension Scheme?", "language": "en",
     "desc": "nps_scheme"},
    {"query": "Tell me about NREGA employment guarantee", "language": "en",
     "desc": "nrega_info"},
    {"query": "What is Indira Awas Yojana?", "language": "en",
     "desc": "iay_info"},
    {"query": "What are the benefits for small farmers?", "language": "en",
     "desc": "small_farmer_benefits"},
    {"query": "How many installments are paid per year?", "language": "en",
     "desc": "installments_per_year"},

    # Hindi queries
    {"query": "PM-KISAN योजना क्या है?", "language": "hi",
     "desc": "hindi_what_is_pmkisan"},
    {"query": "किसान सम्मान निधि के लिए कौन पात्र है?", "language": "hi",
     "desc": "hindi_eligibility"},
    {"query": "PM-KISAN में कितना पैसा मिलता है?", "language": "hi",
     "desc": "hindi_amount"},

    # Telugu queries
    {"query": "PM-KISAN పథకం ఏమిటి?", "language": "te",
     "desc": "telugu_what_is_pmkisan"},
    {"query": "PM-KISAN కు ఎవరు అర్హులు?", "language": "te",
     "desc": "telugu_eligibility"},

    # Tamil queries
    {"query": "PM-KISAN திட்டம் என்ன?", "language": "ta",
     "desc": "tamil_what_is_pmkisan"},
    {"query": "PM-KISAN க்கு யார் தகுதி?", "language": "ta",
     "desc": "tamil_eligibility"},

    # Edge cases
    {"query": "What is the weather today?", "language": "en",
     "desc": "edge_irrelevant_question"},
    {"query": "x", "language": "en",
     "desc": "edge_single_char"},
    {"query": "Tell me everything about every scheme ever created in India since independence including all amendments", "language": "en",
     "desc": "edge_very_long_question"},
]


def test_text_query(idx, q):
    desc = q["desc"]
    log(f"TEST [{idx+1}/{len(TEXT_QUERIES)}]: Text query ({q['language']}): {q['query'][:60]}...")
    start = time.time()
    try:
        r = requests.post(
            f"{API}/query/text",
            json={"query": q["query"], "language": q["language"]},
            timeout=60,
        )
        elapsed = round(time.time() - start, 2)
        body = r.json()
        result = {
            "test": desc,
            "input": q,
            "status_code": r.status_code,
            "elapsed_seconds": elapsed,
            "body": body,
        }
        save("text_queries", f"{idx+1:02d}_{desc}", result)

        if r.status_code == 200:
            answer_preview = body.get("answer", "")[:120]
            n_citations = len(body.get("citations", []))
            proc_ms = body.get("processing_time_ms", "?")
            log(f"  → 200 | {proc_ms}ms | {n_citations} citations | {answer_preview}...")
        else:
            log(f"  → {r.status_code}: {body}")
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        result = {"test": desc, "input": q, "error": str(e), "elapsed_seconds": elapsed}
        save("text_queries", f"{idx+1:02d}_{desc}", result)
        log(f"  → ERROR ({elapsed}s): {e}")


# ── 4. Voice queries ─────────────────────────────────────────────────────────

VOICE_TESTS = [
    {"language": "en", "format": "wav", "desc": "english_wav"},
    {"language": "en", "format": "mp3", "desc": "english_mp3"},
    {"language": "hi", "format": "wav", "desc": "hindi_wav"},
    {"language": "hi", "format": "mp3", "desc": "hindi_mp3"},
    {"language": "te", "format": "wav", "desc": "telugu_wav"},
    {"language": "ta", "format": "mp3", "desc": "tamil_mp3"},
]


def test_voice_query(idx, vt):
    desc = vt["desc"]
    lang = vt["language"]
    fmt = vt["format"]
    log(f"TEST [{idx+1}/{len(VOICE_TESTS)}]: Voice query ({lang}/{fmt}): {desc}")

    # Generate test audio
    if fmt == "wav":
        audio_bytes = make_wav(duration_sec=2)
        filename = "test_query.wav"
        mime = "audio/wav"
    else:
        audio_bytes = make_silent_mp3()
        filename = "test_query.mp3"
        mime = "audio/mpeg"

    start = time.time()
    try:
        r = requests.post(
            f"{API}/query/voice",
            files={"audio": (filename, audio_bytes, mime)},
            data={"language": lang},
            timeout=180,
        )
        elapsed = round(time.time() - start, 2)
        body = r.json()
        result = {
            "test": desc,
            "input": {"language": lang, "format": fmt, "audio_size_bytes": len(audio_bytes)},
            "status_code": r.status_code,
            "elapsed_seconds": elapsed,
            "body": body,
        }
        save("voice_queries", f"{idx+1:02d}_{desc}", result)

        if r.status_code == 200:
            transcript = body.get("transcribed_text", "")[:80]
            answer = body.get("answer_text", "")[:80]
            has_audio = bool(body.get("audio_url"))
            log(f"  → 200 | {elapsed}s | audio_url={'yes' if has_audio else 'no'}")
            log(f"    transcript: {transcript}")
            log(f"    answer: {answer}...")
        else:
            log(f"  → {r.status_code} ({elapsed}s): {json.dumps(body)[:200]}")
    except requests.exceptions.Timeout:
        elapsed = round(time.time() - start, 2)
        result = {"test": desc, "input": {"language": lang, "format": fmt}, "error": "timeout", "elapsed_seconds": elapsed}
        save("voice_queries", f"{idx+1:02d}_{desc}", result)
        log(f"  → TIMEOUT after {elapsed}s")
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        result = {"test": desc, "input": {"language": lang, "format": fmt}, "error": str(e), "elapsed_seconds": elapsed}
        save("voice_queries", f"{idx+1:02d}_{desc}", result)
        log(f"  → ERROR ({elapsed}s): {e}")


# ── 5. Validation / edge-case tests ─────────────────────────────────────────

def test_invalid_language():
    log("TEST: Text query with invalid language")
    r = requests.post(f"{API}/query/text", json={"query": "test", "language": "xx"}, timeout=30)
    result = {"test": "invalid_language", "status_code": r.status_code, "body": r.json()}
    save("text_queries", "90_invalid_language", result)
    log(f"  → {r.status_code}: {r.json()}")


def test_empty_query():
    log("TEST: Text query with empty string")
    r = requests.post(f"{API}/query/text", json={"query": "", "language": "en"}, timeout=30)
    result = {"test": "empty_query", "status_code": r.status_code, "body": r.json()}
    save("text_queries", "91_empty_query", result)
    log(f"  → {r.status_code}: {r.json()}")


def test_missing_audio():
    log("TEST: Voice query with no audio file")
    try:
        r = requests.post(f"{API}/query/voice", data={"language": "en"}, timeout=15)
        result = {"test": "missing_audio", "status_code": r.status_code, "body": r.json()}
    except Exception as e:
        result = {"test": "missing_audio", "error": str(e)}
    save("voice_queries", "90_missing_audio", result)
    log(f"  → {result.get('status_code', 'error')}: {result.get('body', result.get('error'))}")


def test_voice_invalid_language():
    log("TEST: Voice query with invalid language")
    audio = make_silent_mp3()
    r = requests.post(
        f"{API}/query/voice",
        files={"audio": ("test.mp3", audio, "audio/mpeg")},
        data={"language": "xx"},
        timeout=15,
    )
    result = {"test": "voice_invalid_lang", "status_code": r.status_code, "body": r.json()}
    save("voice_queries", "91_invalid_language", result)
    log(f"  → {r.status_code}: {r.json()}")


# ── Summary ──────────────────────────────────────────────────────────────────

def generate_summary():
    """Read all saved results and produce a summary."""
    summary = {
        "timestamp": datetime.now().isoformat(),
        "api_endpoint": API,
        "text_queries": {"total": 0, "passed": 0, "failed": 0, "results": []},
        "voice_queries": {"total": 0, "passed": 0, "failed": 0, "results": []},
        "document_queries": {"total": 0, "passed": 0, "failed": 0, "results": []},
    }

    for folder in ["text_queries", "voice_queries", "document_queries"]:
        section = summary[folder]
        dirpath = os.path.join(RESULTS, folder)
        for fname in sorted(os.listdir(dirpath)):
            if not fname.endswith(".json"):
                continue
            with open(os.path.join(dirpath, fname), encoding="utf-8") as f:
                data = json.load(f)
            status = data.get("status_code", 0)
            passed = status in (200, 404, 400, 422)  # expected responses
            section["total"] += 1
            if passed:
                section["passed"] += 1
            else:
                section["failed"] += 1
            section["results"].append({
                "file": fname,
                "status_code": status,
                "passed": passed,
                "error": data.get("error"),
                "elapsed": data.get("elapsed_seconds"),
            })

    save("", "SUMMARY", summary)
    return summary


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 70)
    print("  JANSAHAYAK RIGOROUS END-TO-END TESTING")
    print("=" * 70)
    total_start = time.time()

    # 1. Health
    test_health()

    # 2. Document operations
    print("\n--- DOCUMENT OPERATIONS ---")
    docs = test_list_documents()
    test_list_documents_by_status("completed")
    test_list_documents_by_status("pending")
    test_list_documents_by_status("failed")
    if docs:
        test_document_status(docs[0]["document_id"], docs[0]["filename"])
    test_document_not_found()

    # 3. Text queries
    print("\n--- TEXT QUERIES ---")
    for i, q in enumerate(TEXT_QUERIES):
        test_text_query(i, q)

    # 4. Edge cases
    print("\n--- EDGE CASES (TEXT) ---")
    test_invalid_language()
    test_empty_query()

    # 5. Voice queries
    print("\n--- VOICE QUERIES ---")
    for i, vt in enumerate(VOICE_TESTS):
        test_voice_query(i, vt)

    # 6. Voice edge cases
    print("\n--- EDGE CASES (VOICE) ---")
    test_missing_audio()
    test_voice_invalid_language()

    # 7. Summary
    print("\n--- GENERATING SUMMARY ---")
    summary = generate_summary()
    total_elapsed = round(time.time() - total_start, 1)

    print("\n" + "=" * 70)
    print(f"  TESTING COMPLETE in {total_elapsed}s")
    print(f"  Text queries:     {summary['text_queries']['passed']}/{summary['text_queries']['total']} passed")
    print(f"  Voice queries:    {summary['voice_queries']['passed']}/{summary['voice_queries']['total']} passed")
    print(f"  Document queries: {summary['document_queries']['passed']}/{summary['document_queries']['total']} passed")
    print(f"  Results saved to: {RESULTS}/")
    print("=" * 70)
