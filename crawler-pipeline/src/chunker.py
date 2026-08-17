"""
Telekom standartlarını clause/section bazında chunk'lara ayırır.

3GPP ve IETF dokümanlarının bölüm yapıları aynı olmadığı için
organizasyona göre farklı heading kontrolleri uygulanır.

IETF RFC dokümanlarında section başlıkları farklı biçimlerde
bulunabildiği için Table of Contents tabanlı doğrulama uygulanır.

Desteklenen IETF örnekleri:

1 Introduction

1. Introduction

ve PDF/text extraction sonrasında:

1
Introduction

veya:

1
.  Introduction
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
# Örnek:
#
# 9.1.3.4.2 Warning Message Delivery Procedure
# 9.2.15 Void
# ---------------------------------------------------------

GENERIC_CLAUSE_HEADING = re.compile(
    r"^(\d+(?:\.\d+)*)[ \t]+(.+)$"
)


# ---------------------------------------------------------
# IETF / RFC TEK SATIR HEADING
#
# Desteklenen örnekler:
#
# 1 Introduction
# 13.2.1 Creating the Initial INVITE
#
# veya:
#
# 1. Introduction
# 13.2.1. Creating the Initial INVITE
#
# İlk section numarasını 1-99 ile sınırlıyoruz.
#
# Böylece:
#
# 200 OK
# 488 Not Acceptable Here
# 5061 ...
#
# gibi değerlerin section sanılması azaltılır.
# ---------------------------------------------------------

IETF_SECTION_HEADING = re.compile(
    r"^([1-9]\d?(?:\.\d+)*)\.?[ \t]+(.+)$"
)


# ---------------------------------------------------------
# IETF / RFC SADECE SECTION NUMARASI
#
# Text extraction bazı RFC'lerde:
#
# 1
# Introduction
#
# bazı RFC'lerde:
#
# 1
# .  Introduction
#
# üretmektedir.
# ---------------------------------------------------------

IETF_SECTION_NUMBER = re.compile(
    r"^([1-9]\d?(?:\.\d+)*)\.?$"
)


# ---------------------------------------------------------
# RFC Table of Contents - tek satır biçimi
#
# Örnek:
#
# 10.2.1.2 Preferences among Contact Addresses ........ 61
# ---------------------------------------------------------

RFC_TOC_SINGLE_LINE = re.compile(
    r"^\s*"
    r"([1-9]\d?(?:\.\d+)*)"
    r"\.?"
    r"\s+"
    r"(.+?)"
    r"\s+\.{2,}\s*"
    r"(\d+)"
    r"\s*$"
)


# ---------------------------------------------------------
# Eski TOC kontrolü
#
# _match_heading fallback modunda kullanılabilir.
# ---------------------------------------------------------

RFC_TOC_LINE = re.compile(
    r"^\s*"
    r"\d+(?:\.\d+)*"
    r"\.?"
    r"\s+"
    r".+"
    r"\.{2,}"
    r"\s*\d+"
    r"\s*$"
)


# ---------------------------------------------------------
# RFC TOC PAGE NUMBER
#
# Split edilmiş TOC örneği:
#
# 13.2.1
# Creating the Initial INVITE ....................
# 78
# ---------------------------------------------------------

RFC_PAGE_NUMBER = re.compile(
    r"^\d{1,4}$"
)


# ---------------------------------------------------------
# 3GPP Table of Contents
#
# Örnek:
#
# 9.1.3.4.2    Warning Message Delivery Procedure    27
#
# Son sayı sayfa numarasıdır.
# ---------------------------------------------------------

GPP_TOC_LINE = re.compile(
    r"^\s*\d+(?:\.\d+)*[ \t]+.+[ \t]+\d+\s*$"
)


# =========================================================
# GENEL YARDIMCI FONKSİYONLAR
# =========================================================

def _normalize_whitespace(
    text: str,
) -> str:
    """
    Birden fazla boşluğu tek boşluğa indirger.
    """

    return re.sub(
        r"\s+",
        " ",
        text or "",
    ).strip()


def _clean_rfc_title(
    text: str,
) -> str:
    """
    RFC başlıklarını karşılaştırmaya uygun hâle getirir.

    Örneğin:

    '.  Introduction'
        ->
    'Introduction'

    'Introduction .......................'
        ->
    'Introduction'
    """

    value = (
        text or ""
    ).strip()

    # RFC 6733 benzeri extraction:
    #
    # .  Introduction
    #
    # başındaki tek noktayı temizle.
    value = re.sub(
        r"^\.\s*",
        "",
        value,
    )

    # TOC dot leader:
    #
    # Introduction ........................
    #
    # kısmını temizle.
    value = re.sub(
        r"\s*\.{2,}.*$",
        "",
        value,
    )

    return _normalize_whitespace(
        value
    )


def _titles_match(
    left: str,
    right: str,
) -> bool:
    """
    İki RFC section başlığının aynı olup olmadığını
    normalize ederek karşılaştırır.
    """

    return (
        _clean_rfc_title(left).casefold()
        ==
        _clean_rfc_title(right).casefold()
    )


# =========================================================
# IETF TABLE OF CONTENTS
# =========================================================

def _find_ietf_toc_start(
    lines: list[str],
) -> int | None:
    """
    RFC içerisindeki Table of Contents başlangıcını bulur.
    """

    for index, line in enumerate(lines):

        normalized = (
            line.strip()
            .casefold()
        )

        if normalized in (
            "table of contents",
            "contents",
        ):
            return index

    return None


def _extract_ietf_toc(
    lines: list[str],
) -> tuple[
    dict[str, str],
    int | None,
    int | None,
]:
    """
    RFC Table of Contents içerisinden:

        section_number -> section_title

    haritasını çıkarır.

    Hem tek satırlı hem de çok satırlı extraction
    formatlarını destekler.

    Returns:
        (
            toc_sections,
            toc_start,
            toc_end
        )
    """

    toc_start = _find_ietf_toc_start(
        lines
    )

    if toc_start is None:
        return {}, None, None

    sections: dict[
        str,
        str,
    ] = {}

    toc_end = toc_start

    # Çok büyük RFC'lerde bile TOC genellikle ilk
    # birkaç bin satır içerisindedir.
    scan_end = min(
        len(lines),
        toc_start + 3000,
    )

    i = toc_start + 1

    last_match_index = toc_start

    while i < scan_end:

        stripped = lines[i].strip()

        # -------------------------------------------------
        # FORMAT 1
        #
        # 13.2.1 Creating the Initial INVITE ...... 78
        # -------------------------------------------------

        single_match = (
            RFC_TOC_SINGLE_LINE.match(
                stripped
            )
        )

        if single_match:

            section_number = (
                single_match
                .group(1)
                .strip()
            )

            title = _clean_rfc_title(
                single_match.group(2)
            )

            if (
                section_number
                and title
                and section_number
                not in sections
            ):
                sections[
                    section_number
                ] = title

            toc_end = i
            last_match_index = i

            i += 1
            continue

        # -------------------------------------------------
        # FORMAT 2
        #
        # 13.2.1
        # Creating the Initial INVITE ............
        # 78
        #
        # veya:
        #
        # 1
        # . Introduction .........................
        # 7
        # -------------------------------------------------

        section_match = (
            IETF_SECTION_NUMBER.fullmatch(
                stripped
            )
        )

        if section_match:

            section_number = (
                section_match
                .group(1)
            )

            title_lines: list[str] = []

            j = i + 1

            # Başlık extraction sırasında birkaç satıra
            # bölünmüş olabilir.
            max_title_end = min(
                len(lines),
                i + 7,
            )

            page_found = False

            while j < max_title_end:

                candidate = (
                    lines[j].strip()
                )

                if not candidate:
                    break

                # Son satır yalnızca sayfa numarasıysa:
                #
                # 61
                if RFC_PAGE_NUMBER.fullmatch(
                    candidate
                ):

                    combined_title = " ".join(
                        title_lines
                    )

                    # TOC olduğundan emin olmak için
                    # title bölümünde dot leader bulunmasını
                    # bekliyoruz.
                    if (
                        title_lines
                        and ".." in combined_title
                    ):

                        title = _clean_rfc_title(
                            combined_title
                        )

                        if (
                            title
                            and section_number
                            not in sections
                        ):
                            sections[
                                section_number
                            ] = title

                        toc_end = j
                        last_match_index = j

                        page_found = True

                    break

                title_lines.append(
                    candidate
                )

                j += 1

            if page_found:
                i = j + 1
                continue

        # -------------------------------------------------
        # TOC bittiyse sonsuza kadar tarama.
        #
        # Son başarılı entry'den sonra uzun süre yeni
        # entry gelmiyorsa gerçek içerik başlamış olabilir.
        # -------------------------------------------------

        if (
            sections
            and (
                i - last_match_index
            ) > 150
        ):
            break

        i += 1

    return (
        sections,
        toc_start,
        toc_end,
    )


# =========================================================
# IETF GERÇEK İÇERİK BAŞLANGICI
# =========================================================

def _match_ietf_heading_against_toc(
    lines: list[str],
    index: int,
    toc_sections: dict[str, str],
):
    """
    Verilen satırın gerçek RFC section heading olup olmadığını
    TOC whitelist kullanarak kontrol eder.

    Returns:

        (section_number, title, consumed_lines)

    veya:

        None
    """

    if index >= len(lines):
        return None

    raw = lines[index]

    candidate = raw.strip()

    if not candidate:
        return None

    # -------------------------------------------------
    # TEK SATIR
    #
    # 1 Introduction
    #
    # veya:
    #
    # 1. Introduction
    # -------------------------------------------------

    same_line_match = (
        IETF_SECTION_HEADING.fullmatch(
            candidate
        )
    )

    if same_line_match:

        section_number = (
            same_line_match.group(1)
        )

        title = _clean_rfc_title(
            same_line_match.group(2)
        )

        expected_title = (
            toc_sections.get(
                section_number
            )
        )

        if (
            expected_title is not None
            and _titles_match(
                title,
                expected_title,
            )
        ):
            return (
                section_number,
                expected_title,
                1,
            )

    # -------------------------------------------------
    # İKİ SATIR
    #
    # 1
    # Introduction
    #
    # veya:
    #
    # 1
    # . Introduction
    # -------------------------------------------------

    number_match = (
        IETF_SECTION_NUMBER.fullmatch(
            candidate
        )
    )

    if (
        number_match
        and index + 1 < len(lines)
    ):

        section_number = (
            number_match.group(1)
        )

        expected_title = (
            toc_sections.get(
                section_number
            )
        )

        if expected_title is None:
            return None

        title_candidate = (
            _clean_rfc_title(
                lines[index + 1]
            )
        )

        if _titles_match(
            title_candidate,
            expected_title,
        ):
            return (
                section_number,
                expected_title,
                2,
            )

    return None


def _find_ietf_content_start(
    lines: list[str],
    toc_sections: dict[str, str],
    toc_end: int | None,
) -> int | None:
    """
    TOC bittikten sonra gerçek RFC section içeriğinin
    başladığı satırı bulur.

    Genellikle:

        1
        Introduction

    veya:

        1. Introduction

    ile başlar.
    """

    if not toc_sections:
        return None

    search_start = (
        (toc_end + 1)
        if toc_end is not None
        else 0
    )

    # İlk birkaç TOC section'ını kullanarak gerçek
    # içerik başlangıcını arıyoruz.
    first_sections = list(
        toc_sections.keys()
    )[:10]

    first_section_set = set(
        first_sections
    )

    for index in range(
        search_start,
        len(lines),
    ):

        heading = (
            _match_ietf_heading_against_toc(
                lines=lines,
                index=index,
                toc_sections=toc_sections,
            )
        )

        if heading is None:
            continue

        section_number = heading[0]

        if section_number in first_section_set:
            return index

    return None


# =========================================================
# IETF SPLITTER
# =========================================================

def _split_ietf_clauses(
    document_text: str,
) -> list[
    tuple[str, str, str]
]:
    """
    IETF RFC dokümanını section bazında ayırır.

    Öncelikli yöntem:

        Table of Contents whitelist

    Böylece metin içerisindeki section referansları
    yanlışlıkla heading kabul edilmez.
    """

    lines = (
        document_text.splitlines()
    )

    (
        toc_sections,
        _toc_start,
        toc_end,
    ) = _extract_ietf_toc(
        lines
    )

    clauses: list[
        tuple[
            str,
            str,
            list[str],
        ]
    ] = []

    current = None

    # -------------------------------------------------
    # TOC bulunduysa güvenli parser kullan.
    # -------------------------------------------------

    if toc_sections:

        content_start = (
            _find_ietf_content_start(
                lines=lines,
                toc_sections=toc_sections,
                toc_end=toc_end,
            )
        )

        if content_start is None:
            content_start = (
                (toc_end + 1)
                if toc_end is not None
                else 0
            )

        i = content_start

        while i < len(lines):

            heading = (
                _match_ietf_heading_against_toc(
                    lines=lines,
                    index=i,
                    toc_sections=toc_sections,
                )
            )

            if heading is not None:

                (
                    section_number,
                    section_title,
                    consumed_lines,
                ) = heading

                if current:
                    clauses.append(
                        current
                    )

                current = (
                    section_number,
                    section_title,
                    [],
                )

                i += consumed_lines
                continue

            if current:
                current[2].append(
                    lines[i]
                )

            i += 1

        if current:
            clauses.append(
                current
            )

        return [
            (
                clause_no,
                clause_title,
                "\n".join(body).strip(),
            )
            for (
                clause_no,
                clause_title,
                body,
            ) in clauses
        ]

    # -------------------------------------------------
    # FALLBACK
    #
    # Bazı RFC'lerde Table of Contents olmayabilir.
    #
    # Bu durumda eski tek-satır heading davranışını
    # koruyoruz.
    # -------------------------------------------------

    for line in lines:

        match = _match_heading(
            line=line,
            doc_org="IETF",
        )

        if match:

            if current:
                clauses.append(
                    current
                )

            current = (
                match.group(1),
                _clean_rfc_title(
                    match.group(2)
                ),
                [],
            )

        elif current:

            current[2].append(
                line
            )

    if current:
        clauses.append(
            current
        )

    return [
        (
            clause_no,
            clause_title,
            "\n".join(body).strip(),
        )
        for (
            clause_no,
            clause_title,
            body,
        ) in clauses
    ]


# =========================================================
# HEADING MATCH
# =========================================================

def _match_heading(
    line: str,
    doc_org: str,
):
    """
    Organizasyona uygun section/clause heading
    eşleşmesini döndürür.

    IETF için bu fonksiyon esas olarak fallback
    parser tarafından kullanılır.

    Normal IETF parsing TOC whitelist üzerinden
    _split_ietf_clauses içerisinde yapılır.
    """

    candidate = line.rstrip()

    if not candidate:
        return None

    # Girintili örnek satırlarını heading olarak
    # değerlendirme.
    if candidate != candidate.lstrip():
        return None

    org = (
        doc_org or ""
    ).strip().upper()

    # -------------------------------------------------
    # IETF
    # -------------------------------------------------

    if org == "IETF":

        if RFC_TOC_LINE.match(
            candidate
        ):
            return None

        return (
            IETF_SECTION_HEADING.match(
                candidate
            )
        )

    # -------------------------------------------------
    # 3GPP
    # -------------------------------------------------

    if org == "3GPP":

        # İçindekiler tablosundaki:
        #
        # 9.1.3.4.2  Başlık  27
        #
        # gibi satırları reddet.
        if GPP_TOC_LINE.match(
            candidate
        ):
            return None

        match = (
            GENERIC_CLAUSE_HEADING.match(
                candidate
            )
        )

        if not match:
            return None

        clause_number = (
            match.group(1)
        )

        # "650 Route des Lucioles..."
        # gibi adres satırlarını clause kabul etme.
        #
        # Noktalı gerçek clause'lara dokunmuyoruz:
        #
        # 9.1.3.4.2
        if "." not in clause_number:

            try:

                if int(
                    clause_number
                ) > 99:
                    return None

            except ValueError:
                return None

        return match

    # -------------------------------------------------
    # GENERIC
    # -------------------------------------------------

    return (
        GENERIC_CLAUSE_HEADING.match(
            candidate
        )
    )


# =========================================================
# ANA CLAUSE SPLITTER
# =========================================================

def split_into_clauses(
    document_text: str,
    doc_org: str,
) -> list[
    tuple[str, str, str]
]:
    """
    Dokümanı clause/section bazında ayırır.

    Returns:

        (
            clause_number,
            clause_title,
            body_text
        )
    """

    org = (
        doc_org or ""
    ).strip().upper()

    # -------------------------------------------------
    # IETF
    #
    # RFC'ler için özel TOC tabanlı parser.
    # -------------------------------------------------

    if org == "IETF":

        return _split_ietf_clauses(
            document_text
        )

    # -------------------------------------------------
    # 3GPP / GENERIC
    # -------------------------------------------------

    lines = (
        document_text.splitlines()
    )

    clauses: list[
        tuple[
            str,
            str,
            list[str],
        ]
    ] = []

    current = None

    # 3GPP dokümanlarında ön kapak/sürüm
    # gürültüsünü atlamak için gerçek içerik
    # "1 Scope" ile başlayana kadar bekliyoruz.
    gpp_content_started = (
        org != "3GPP"
    )

    for line in lines:

        # -------------------------------------------------
        # 3GPP gerçek içerik başlangıcı
        # -------------------------------------------------

        if (
            org == "3GPP"
            and not gpp_content_started
        ):

            scope_match = (
                GENERIC_CLAUSE_HEADING.match(
                    line.strip()
                )
            )

            if (
                scope_match
                and scope_match.group(1) == "1"
                and (
                    scope_match
                    .group(2)
                    .strip()
                    .lower()
                    == "scope"
                )
            ):
                gpp_content_started = True

            else:
                continue

        # -------------------------------------------------
        # 3GPP TOC temizliği
        # -------------------------------------------------

        if org == "3GPP":

            if GPP_TOC_LINE.match(
                line.strip()
            ):
                continue

        # -------------------------------------------------
        # Heading eşleşmesi
        # -------------------------------------------------

        match = _match_heading(
            line=line,
            doc_org=doc_org,
        )

        if match:

            if current:
                clauses.append(
                    current
                )

            current = (
                match.group(1),
                match.group(2).strip(),
                [],
            )

        elif current:

            current[2].append(
                line
            )

    if current:

        clauses.append(
            current
        )

    return [
        (
            clause_no,
            clause_title,
            "\n".join(body).strip(),
        )
        for (
            clause_no,
            clause_title,
            body,
        ) in clauses
    ]


# =========================================================
# UZUN TEXT SPLITTER
# =========================================================

def _split_long_text(
    title: str,
    body: str,
    max_chars: int = MAX_CHUNK_CHARS,
    overlap_chars: int = CHUNK_OVERLAP_CHARS,
) -> list[str]:
    """
    Uzun clause içeriklerini daha küçük ve overlap'li
    alt chunk'lara böler.

    Her alt chunk'ın başına clause başlığı tekrar eklenir.

    Gerçek clause numarası değiştirilmez.
    """

    title = title.strip()
    body = body.strip()

    if not body:

        return (
            [title]
            if title
            else []
        )

    full_text = (
        f"{title}\n{body}"
        if title
        else body
    )

    # Zaten yeterince küçükse bölme.
    if len(
        full_text
    ) <= max_chars:

        return [
            full_text
        ]

    chunks: list[str] = []

    # Her alt parçanın başında title olacağı için
    # body tarafında kullanılabilecek maksimum alanı
    # hesapla.
    title_size = (
        len(title) + 1
        if title
        else 0
    )

    available_body_chars = (
        max_chars
        - title_size
    )

    if available_body_chars <= 0:

        available_body_chars = (
            max_chars
        )

    start = 0

    while start < len(body):

        end = min(
            start
            + available_body_chars,
            len(body),
        )

        # -------------------------------------------------
        # Metni mümkün olduğunca doğal sınırdan kes.
        #
        # Öncelik:
        #
        # 1. paragraf / satır sonu
        # 2. cümle sonu
        # 3. boşluk
        # 4. karakter sınırı
        # -------------------------------------------------

        if end < len(body):

            search_start = (
                start
                + int(
                    available_body_chars
                    * 0.5
                )
            )

            candidate_end = (
                body.rfind(
                    "\n",
                    search_start,
                    end,
                )
            )

            if candidate_end <= start:

                candidate_end = (
                    body.rfind(
                        ". ",
                        search_start,
                        end,
                    )
                )

                if candidate_end > start:
                    candidate_end += 1

            if candidate_end <= start:

                candidate_end = (
                    body.rfind(
                        " ",
                        search_start,
                        end,
                    )
                )

            if candidate_end > start:
                end = candidate_end

        part = (
            body[
                start:end
            ].strip()
        )

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

        # Bir kelimenin ortasından başlamamak için
        # overlap başlangıcını sonraki boşluğa kaydır.
        if next_start > 0:

            next_space = (
                body.find(
                    " ",
                    next_start,
                    end,
                )
            )

            if (
                next_space != -1
                and next_space < end
            ):
                next_start = (
                    next_space + 1
                )

        # Sonsuz döngü koruması.
        if next_start <= start:
            next_start = end

        start = next_start

    return chunks


# =========================================================
# BUILD CHUNKS
# =========================================================

def build_chunks(
    document_text: str,
    doc_org: str,
    doc_code: str,
    version: str,
    source_url: str | None = None,
) -> list[Chunk]:
    """
    Ham doküman metnini clause/section bazında
    Chunk nesnelerine çevirir.

    Küçük clause'lar tek chunk olarak kalır.

    MAX_CHUNK_CHARS sınırını aşan clause'lar
    overlap'li alt chunk'lara bölünür.

    Alt chunk'ların tamamında gerçek clause numarası
    ve clause title korunur.
    """

    chunks: list[
        Chunk
    ] = []

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
            clause_title
            or ""
        ).strip()

        body_clean = (
            body
            or ""
        ).strip()

        # -------------------------------------------------
        # VOID kontrolü
        # -------------------------------------------------

        is_void = (
            title_clean
            .lower()
            .startswith(
                "void"
            )
            or (
                body_clean.lower()
                == "void"
            )
            or (
                body_clean.lower()
                == "void."
            )
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

        text_parts = (
            _split_long_text(
                title=title_clean,
                body=body_clean,
            )
        )

        for text_part in text_parts:

            clean_part = (
                text_part
                or ""
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
