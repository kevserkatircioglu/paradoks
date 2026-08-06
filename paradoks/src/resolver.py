"""Resolves a Reference to a real URL.

Chain: deterministic URL template -> official index page -> site-restricted
search -> UNRESOLVED.
"""

import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("GOOGLE_API_KEY")
CX = os.environ.get("GOOGLE_CX")


def _resolve_3gpp(ref: Reference) -> ResolvedSource:
    parts = ref.code.split()
    if len(parts) == 2:
        series = parts[1].split(".")[0]
        url = f"https://www.3gpp.org/ftp/Specs/archive/{series}_series/{parts[1]}/"
        return ResolvedSource(reference=ref, status=DocStatus.PENDING, source_url=url)
    return ResolvedSource(reference=ref, status=DocStatus.UNRESOLVED)


def _resolve_ietf(ref: Reference) -> ResolvedSource:
    url = f"https://www.rfc-editor.org/rfc/rfc{ref.code.strip()}.html"
    return ResolvedSource(reference=ref, status=DocStatus.PENDING, source_url=url)

def _resolve_etsi(ref: Reference) -> ResolvedSource:
    code_clean = ref.code.replace("TS", "").strip()
    parts = code_clean.split()
    if len(parts) >= 2:
        series = parts[0]
        full_num = "".join(parts)
        url = f"https://www.etsi.org/deliver/etsi_ts/{series}000_{series}999/{full_num}/"
        return ResolvedSource(reference=ref, status=DocStatus.PENDING, source_url=url)
    return ResolvedSource(reference=ref, status=DocStatus.UNRESOLVED)

def _resolve_itu(ref: Reference) -> ResolvedSource:
    # Örn: G.711 -> https://www.itu.int/rec/T-REC-G.711/en
    code_clean = ref.code.strip()
    url = f"https://www.itu.int/rec/T-REC-{code_clean}/en"
    return ResolvedSource(reference=ref, status=DocStatus.PENDING, source_url=url)


def _resolve_gsma(ref: Reference) -> ResolvedSource:
    # GSMA PRD belgeleri genelde resmi doküman arama sayfasına indekslenir
    code_clean = ref.code.strip()
    url = f"https://www.gsma.com/newsroom/all-documents/?search={code_clean}"
    return ResolvedSource(reference=ref, status=DocStatus.PENDING, source_url=url)


def _resolve_atis(ref: Reference) -> ResolvedSource:
    # Örn: 1000053 -> ATIS standartları genelde ANSI üzerinden yayınlanır
    code_clean = ref.code.replace("ATIS-", "").replace("-", "").strip()
    url = f"https://webstore.ansi.org/Standards/ATIS/atis{code_clean}"
    return ResolvedSource(reference=ref, status=DocStatus.PENDING, source_url=url)

DETERMINISTIC_RESOLVERS = {
    "3GPP": _resolve_3gpp,
    "IETF": _resolve_ietf,
    "ETSI": _resolve_etsi,
    "ITU": _resolve_itu,
    "GSMA": _resolve_gsma,
    "ATIS": _resolve_atis,
}


def resolve_official_index(ref: Reference) -> ResolvedSource:
    # TODO: query org's own document index (e.g. GSMA PRD list, ETSI portal)
    raise NotImplementedError





def resolve(ref: Reference) -> ResolvedSource:
    if ref.org in DETERMINISTIC_RESOLVERS:
        return DETERMINISTIC_RESOLVERS[ref.org](ref)

    return ResolvedSource(reference=ref, status=DocStatus.UNRESOLVED)

if __name__ == "__main__":
    print("--- Deterministik Çözümleyici Testleri ---\n")

    # 1. 3GPP Testi
    test_ref_3gpp = Reference(org="3GPP", code="TS 38.211", title="", raw_text="3GPP TS 38.211")
    result_3gpp = resolve(test_ref_3gpp)
    print(f"3GPP URL: {result_3gpp.source_url}")

    # 2. IETF Testi
    test_ref_ietf = Reference(org="IETF", code="9000", title="", raw_text="RFC 9000")
    result_ietf = resolve(test_ref_ietf)
    print(f"IETF URL: {result_ietf.source_url}")

    # 3. ETSI Testi
    test_ref_etsi = Reference(org="ETSI", code="TS 102 900", title="", raw_text="ETSI TS 102 900")
    result_etsi = resolve(test_ref_etsi)
    print(f"ETSI URL: {result_etsi.source_url}")

    # 4. ITU Testi
    test_ref_itu = Reference(org="ITU", code="G.711", title="", raw_text="ITU-T G.711")
    result_itu = resolve(test_ref_itu)
    print(f"ITU URL:  {result_itu.source_url}")

    # 5. GSMA Testi
    test_ref_gsma = Reference(org="GSMA", code="SGP.22", title="", raw_text="GSMA SGP.22")
    result_gsma = resolve(test_ref_gsma)
    print(f"GSMA URL: {result_gsma.source_url}")

    # 6. ATIS Testi
    test_ref_atis = Reference(org="ATIS", code="1000053", title="", raw_text="ATIS 1000053")
    result_atis = resolve(test_ref_atis)
    print(f"ATIS URL: {result_atis.source_url}")
    
    print("\n------------------------------------------")