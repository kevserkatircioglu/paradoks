"""
Telekom standartlar─▒n─▒ clause/section baz─▒nda chunk'lara ay─▒r─▒r.

3GPP ve IETF dok├╝manlar─▒n─▒n b├Âl├╝m yap─▒lar─▒ ayn─▒ olmad─▒─ş─▒ i├ğin
organizasyona g├Âre farkl─▒ heading kontrolleri uygulan─▒r.
"""

import re

from models import Chunk, DocStatus


# ---------------------------------------------------------
# CHUNK AYARLARI
# ---------------------------------------------------------
MAX_CHUNK_CHARS = 2400
CHUNK_OVERLAP_CHARS = 300


# ---------------------------------------------------------
# 3GPP / GENERIC CLAUSE
#
# ├ûrnek:
# 9.1.3.4.2 Warning Message Delivery Procedure
# 9.2.15 Void
# ---------------------------------------------------------
GENERIC_CLAUSE_HEADING = re.compile(
    r"^(\d+(?:\.\d+)*)[ \t]+(.+)$"
)


# ---------------------------------------------------------
# IETF / RFC
#
# Ger├ğek ├Ârnekler:
# 1 Introduction
# 13.2.1 Creating the Initial INVITE
# 21.4.26 488 Not Acceptable Here
#
# ─░lk section numaras─▒n─▒ 1-99 ile s─▒n─▒rland─▒r─▒yoruz.
# B├Âylece:
# 200 OK
# 488 Not Acceptable Here
# 5061 ...
# 239.255.255.1 ...
# gibi de─şerlerin section san─▒lmas─▒n─▒ engelliyoruz.
# ---------------------------------------------------------
IETF_SECTION_HEADING = re.compile(
    r"^([1-9]\d?(?:\.\d+)*)[ \t]+(.+)$"
)


# ---------------------------------------------------------
# RFC Table of Contents
#
# ├ûrnek:
# 10.2.1.2 Preferences among Contact Addresses ............ 61
# ---------------------------------------------------------
RFC_TOC_LINE = re.compile(
    r"^\s*\d+(?:\.\d+)*\s+.+\.{2,}\s*\d+\s*$"
)


# ---------------------------------------------------------
# 3GPP Table of Contents
#
# ├ûrnek:
# 9.1.3.4.2    Warning Message Delivery Procedure    27
#
# Son say─▒ sayfa numaras─▒d─▒r; ger├ğek clause heading de─şildir.
# ---------------------------------------------------------
GPP_TOC_LINE = re.compile(
    r"^\s*\d+(?:\.\d+)*[ \t]+.+[ \t]+\d+\s*$"
)


def _match_heading(
    line: str,
    doc_org: str,
):
    """
    Organizasyona uygun section/clause heading e┼şle┼şmesini d├Ând├╝r├╝r.
    """

    candidate = line.rstrip()

    if not candidate:
        return None

    # Girintili ├Ârnek sat─▒rlar─▒n─▒ heading olarak de─şerlendirme.
    if candidate != candidate.lstrip():
        return None

    org = (doc_org or "").strip().upper()

    if org == "IETF":
        if RFC_TOC_LINE.match(candidate):
            return None

        return IETF_SECTION_HEADING.match(candidate)

    if org == "3GPP":
        # ─░├ğindekiler tablosundaki:
        # 9.1.3.4.2  Ba┼şl─▒k  27
        # gibi sat─▒rlar─▒ reddet.
        if GPP_TOC_LINE.match(candidate):
            return None

        match = GENERIC_CLAUSE_HEADING.match(
            candidate
        )

        if not match:
            return None

        clause_number = match.group(1)

        # "650 Route des Lucioles..." gibi adres sat─▒rlar─▒n─▒
        # clause olarak kabul etme.
        #
        # Noktal─▒ ger├ğek clause'lara dokunmuyoruz:
        # 9.1.3.4.2 vb.
        if "." not in clause_number:
            try:
                if int(clause_number) > 99:
                    return None
            except ValueError:
                return None

        return match

    return GENERIC_CLAUSE_HEADING.match(
        candidate
    )


def split_into_clauses(
    document_text: str,
    doc_org: str,
) -> list[tuple[str, str, str]]:
    """
    Dok├╝man─▒ sat─▒r sat─▒r okuyup clause/section baz─▒nda ay─▒r─▒r.

    Returns:
        (clause_number, clause_title, body_text)
    """

    lines = document_text.splitlines()

    clauses: list[
        tuple[str, str, list[str]]
    ] = []

    current = None

    org = (doc_org or "").strip().upper()

    # 3GPP dok├╝manlar─▒nda ├Ân kapak/s├╝r├╝m g├╝r├╝lt├╝s├╝n├╝ atlamak i├ğin
    # ger├ğek i├ğerik "1 Scope" ile ba┼şlayana kadar bekliyoruz.
    gpp_content_started = org != "3GPP"

    for line in lines:

        # -------------------------------------------------
        # 3GPP ger├ğek i├ğerik ba┼şlang─▒c─▒
        # -------------------------------------------------
        if org == "3GPP" and not gpp_content_started:
            scope_match = GENERIC_CLAUSE_HEADING.match(
                line.strip()
            )

            if (
                scope_match
                and scope_match.group(1) == "1"
                and scope_match.group(2).strip().lower() == "scope"
            ):
                gpp_content_started = True
            else:
                continue

        # -------------------------------------------------
        # TOC temizli─şi
        # -------------------------------------------------
        if org == "IETF":
            if RFC_TOC_LINE.match(
                line.strip()
            ):
                continue

        if org == "3GPP":
            if GPP_TOC_LINE.match(
                line.strip()
            ):
                continue

        # -------------------------------------------------
        # Heading e┼şle┼şmesi
        # -------------------------------------------------
        match = _match_heading(
            line=line,
            doc_org=doc_org,
        )

        if match:
            if current:
                clauses.append(current)

            current = (
                match.group(1),
                match.group(2).strip(),
                [],
            )

        elif current:
            current[2].append(line)

    if current:
        clauses.append(current)

    return [
        (
            clause_no,
            clause_title,
            "\n".join(body).strip(),
        )
        for clause_no, clause_title, body in clauses
    ]


def _split_long_text(
    title: str,
    body: str,
    max_chars: int = MAX_CHUNK_CHARS,
    overlap_chars: int = CHUNK_OVERLAP_CHARS,
) -> list[str]:
    """
    Uzun clause i├ğeriklerini daha k├╝├ğ├╝k ve overlap'li
    alt chunk'lara b├Âler.

    Her alt chunk'─▒n ba┼ş─▒na clause ba┼şl─▒─ş─▒ tekrar eklenir.

    Ger├ğek clause numaras─▒ de─şi┼ştirilmez.
    """

    title = title.strip()
    body = body.strip()

    if not body:
        return [title] if title else []

    full_text = (
        f"{title}\n{body}"
        if title
        else body
    )

    # Zaten yeterince k├╝├ğ├╝kse b├Âlme.
    if len(full_text) <= max_chars:
        return [full_text]

    chunks: list[str] = []

    # Her alt par├ğan─▒n ba┼ş─▒nda title olaca─ş─▒ i├ğin
    # body taraf─▒nda kullan─▒labilecek maksimum alan─▒ hesapla.
    title_size = (
        len(title) + 1
        if title
        else 0
    )

    available_body_chars = (
        max_chars - title_size
    )

    if available_body_chars <= 0:
        available_body_chars = max_chars

    start = 0

    while start < len(body):
        end = min(
            start + available_body_chars,
            len(body),
        )

        # -------------------------------------------------
        # Metni m├╝mk├╝n oldu─şunca do─şal s─▒n─▒rdan kes.
        # ├ûncelik:
        # 1. paragraf / sat─▒r sonu
        # 2. c├╝mle sonu
        # 3. bo┼şluk
        # 4. mecburen karakter s─▒n─▒r─▒
        # -------------------------------------------------
        if end < len(body):
            search_start = start + int(
                available_body_chars * 0.5
            )

            candidate_end = body.rfind(
                "\n",
                search_start,
                end,
            )

            if candidate_end <= start:
                candidate_end = body.rfind(
                    ". ",
                    search_start,
                    end,
                )

                if candidate_end > start:
                    candidate_end += 1

            if candidate_end <= start:
                candidate_end = body.rfind(
                    " ",
                    search_start,
                    end,
                )

            if candidate_end > start:
                end = candidate_end

        part = body[
            start:end
        ].strip()

        if part:
            if title:
                chunk_text = (
                    f"{title}\n{part}"
                )
            else:
                chunk_text = part

            chunks.append(
                chunk_text
            )

        if end >= len(body):
            break

        # -------------------------------------------------
        # Overlap
        # -------------------------------------------------
        next_start = max(
            0,
            end - overlap_chars,
        )

        # Bir kelimenin ortas─▒ndan ba┼şlamamak i├ğin
        # overlap ba┼şlang─▒c─▒n─▒ sonraki bo┼şlu─şa kayd─▒r.
        if next_start > 0:
            next_space = body.find(
                " ",
                next_start,
                end,
            )

            if (
                next_space != -1
                and next_space < end
            ):
                next_start = (
                    next_space + 1
                )

        # Sonsuz d├Âng├╝ korumas─▒.
        if next_start <= start:
            next_start = end

        start = next_start

    return chunks


def build_chunks(
    document_text: str,
    doc_org: str,
    doc_code: str,
    version: str,
    source_url: str | None = None,
) -> list[Chunk]:
    """
    Ham dok├╝man metnini clause/section baz─▒nda
    Chunk nesnelerine ├ğevirir.

    K├╝├ğ├╝k clause'lar tek chunk olarak kal─▒r.

    MAX_CHUNK_CHARS s─▒n─▒r─▒n─▒ a┼şan clause'lar
    overlap'li alt chunk'lara b├Âl├╝n├╝r.

    Alt chunk'lar─▒n tamam─▒nda ger├ğek clause numaras─▒
    ve clause title korunur.
    """

    chunks: list[Chunk] = []

    clauses = split_into_clauses(
        document_text=document_text,
        doc_org=doc_org,
    )

    for (
        clause_no,
        clause_title,
        body,
    ) in clauses:

        title_clean = (
            clause_title or ""
        ).strip()

        body_clean = (
            body or ""
        ).strip()

        # -------------------------------------------------
        # VOID kontrol├╝
        # -------------------------------------------------
        is_void = (
            title_clean.lower().startswith(
                "void"
            )
            or body_clean.lower() == "void"
            or body_clean.lower() == "void."
        )

        if is_void:
            chunks.append(
                Chunk(
                    text="",
                    doc_org=doc_org,
                    doc_code=doc_code,
                    version=version,
                    clause=clause_no,
                    clause_title=title_clean,
                    status=DocStatus.VOID,
                    source_url=source_url,
                )
            )

            continue

        # -------------------------------------------------
        # Normal / uzun clause chunking
        # -------------------------------------------------
        text_parts = _split_long_text(
            title=title_clean,
            body=body_clean,
        )

        for text_part in text_parts:
            clean_part = (
                text_part or ""
            ).strip()

            if not clean_part:
                continue

            chunks.append(
                Chunk(
                    text=clean_part,
                    doc_org=doc_org,
                    doc_code=doc_code,
                    version=version,
                    clause=clause_no,
                    clause_title=title_clean,
                    status=DocStatus.INDEXED,
                    source_url=source_url,
                )
            )

    return chunks
