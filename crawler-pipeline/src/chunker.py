"""
Telekom standartlarını clause/section bazında chunk'lara ayırır.

Desteklenen temel organizasyonlar:

- 3GPP
- IETF
- Generic fallback

3GPP ve IETF dokümanları farklı bölüm yapılarına sahip
olduğundan organizasyona özel parser kullanılır.

Hem 3GPP hem IETF tarafında mümkün olduğunda
Table of Contents (TOC) whitelist olarak kullanılır.

Bu sayede doküman gövdesindeki:

    1 Introduction
    2 Example
    3 Procedure

gibi yerel numaralandırmaların yanlışlıkla gerçek
clause/section olarak kabul edilmesi azaltılır.

3GPP tarafında extraction sırasında clause numarası
kısmen veya tamamen kaybolursa TOC kullanılarak
kontrollü recovery uygulanır.

Desteklenen recovery örnekleri:

    GPRS attach procedures
        ->
    4.1.1 GPRS attach procedures

ve:

    .2 Successful GPRS attach procedures
        ->
    4.1.1.2 Successful GPRS attach procedures

Recovery yalnızca TOC içerisinde tek ve güvenli bir
eşleşme bulunduğunda uygulanır.
"""

import re

from models import Chunk, DocStatus


# =========================================================
# CHUNK AYARLARI
# =========================================================

MAX_CHUNK_CHARS = 2400
CHUNK_OVERLAP_CHARS = 300


# =========================================================
# GENERIC NUMERIC CLAUSE
# =========================================================

GENERIC_CLAUSE_HEADING = re.compile(
    r"^(\d+(?:\.\d+)*)[ \t]+(.+)$"
)


# =========================================================
# 3GPP CLAUSE TOKEN
#
# Desteklenen örnekler:
#
# 0
# 0a
# 0b
# 1
# 1.1
# 9.1.3.4.2
# A
# A.1
# A.1.3.4
# =========================================================

GPP_CLAUSE_TOKEN_PATTERN = (
    r"(?:"
    r"\d+[A-Za-z]?(?:\.\d+)*"
    r"|"
    r"[A-Z](?:\.\d+)*"
    r")"
)


# =========================================================
# 3GPP TEK SATIR HEADING
# =========================================================

GPP_SECTION_HEADING = re.compile(
    rf"^\s*"
    rf"({GPP_CLAUSE_TOKEN_PATTERN})"
    rf"\.?"
    rf"[ \t]+"
    rf"(.+?)"
    rf"\s*$",
    re.IGNORECASE,
)


# =========================================================
# 3GPP RECOVERY - SUFFIX HEADING
#
# Extraction bazı dokümanlarda:
#
# 4.1.1.1
#
# yerine:
#
# .1 Attempted GPRS attach procedures
#
# üretebiliyor.
#
# Birden fazla suffix seviyesi de desteklenir:
#
# .1.2 Title
# =========================================================

GPP_SUFFIX_HEADING = re.compile(
    r"^\s*"
    r"(\.\d+(?:\.\d+)*)"
    r"[ \t]+"
    r"(.+?)"
    r"\s*$"
)


# =========================================================
# 3GPP ANNEX ANA BAŞLIĞI
# =========================================================

GPP_ANNEX_HEADING = re.compile(
    r"^\s*"
    r"Annex[ \t]+"
    r"([A-Z]|\d+)"
    r"(?:[ \t]*\([^)]*\))?"
    r"[ \t]*:"
    r"[ \t]*(.*?)"
    r"\s*$",
    re.IGNORECASE,
)


# =========================================================
# 3GPP TOC ENTRY
# =========================================================

GPP_TOC_ENTRY = re.compile(
    rf"^\s*"
    rf"({GPP_CLAUSE_TOKEN_PATTERN})"
    rf"\.?"
    rf"[ \t]+"
    rf"(.+?)"
    rf"[ \t]+"
    rf"(\d+)"
    rf"\s*$",
    re.IGNORECASE,
)


# =========================================================
# 3GPP ANNEX TOC ENTRY
# =========================================================

GPP_ANNEX_TOC_ENTRY = re.compile(
    r"^\s*"
    r"Annex[ \t]+"
    r"([A-Z]|\d+)"
    r"(?:[ \t]*\([^)]*\))?"
    r"[ \t]*:?"
    r"[ \t]*(.*?)"
    r"[ \t]+"
    r"(\d+)"
    r"\s*$",
    re.IGNORECASE,
)


# =========================================================
# IETF HEADING
# =========================================================

IETF_SECTION_HEADING = re.compile(
    r"^([1-9]\d?(?:\.\d+)*)\.?[ \t]+(.+)$"
)


IETF_SECTION_NUMBER = re.compile(
    r"^([1-9]\d?(?:\.\d+)*)\.?$"
)


# =========================================================
# IETF TOC
# =========================================================

RFC_TOC_SINGLE_LINE = re.compile(
    r"^\s*"
    r"([1-9]\d?(?:\.\d+)*)"
    r"\.?"
    r"\s+"
    r"(.+?)"
    r"(?:"
    r"\s+\.{2,}\s*"
    r"|"
    r"\s{2,}"
    r")"
    r"(\d+)"
    r"\s*$"
)


RFC_TOC_LINE = re.compile(
    r"^\s*"
    r"\d+(?:\.\d+)*"
    r"\.?"
    r"\s+"
    r".+?"
    r"\s+"
    r"(?:\.{2,}\s*)?"
    r"\d{1,4}"
    r"\s*$"
)


RFC_PAGE_NUMBER = re.compile(
    r"^\d{1,4}$"
)


# =========================================================
# GENEL YARDIMCILAR
# =========================================================

def _normalize_whitespace(
    text: str,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        text or "",
    ).strip()


def _clean_title(
    text: str,
) -> str:
    """
    Genel başlık temizliği.
    """

    value = (
        text or ""
    ).strip()

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def _clean_3gpp_title(
    text: str,
) -> str:
    """
    3GPP TOC ve içerik başlıklarını karşılaştırmak
    için normalize eder.

    Scope.
        ->
    Scope

    Scope:
        ->
    Scope
    """

    value = _clean_title(
        text
    )

    value = value.rstrip(
        " \t.:"
    )

    return _normalize_whitespace(
        value
    )


def _3gpp_titles_match(
    left: str,
    right: str,
) -> bool:

    return (
        _clean_3gpp_title(
            left
        ).casefold()
        ==
        _clean_3gpp_title(
            right
        ).casefold()
    )


def _clean_rfc_title(
    text: str,
) -> str:

    value = (
        text or ""
    ).strip()

    value = re.sub(
        r"^\.\s*",
        "",
        value,
    )

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

    return (
        _clean_rfc_title(
            left
        ).casefold()
        ==
        _clean_rfc_title(
            right
        ).casefold()
    )


def _looks_like_rfc_toc_title(
    title: str,
) -> bool:

    cleaned = _clean_rfc_title(
        title
    )

    if not cleaned:
        return False

    if re.fullmatch(
        r"\d+(?:\.\d+)*\.?",
        cleaned,
    ):
        return False

    if not re.search(
        r"[A-Za-z]",
        cleaned,
    ):
        return False

    return True


# =========================================================
# 3GPP TABLE OF CONTENTS
# =========================================================

def _find_3gpp_toc_start(
    lines: list[str],
) -> int | None:
    """
    3GPP dokümanındaki Contents başlangıcını bulur.
    """

    for index, line in enumerate(
        lines
    ):

        normalized = (
            line
            .strip()
            .casefold()
        )

        if normalized in {
            "contents",
            "table of contents",
        }:

            return index

    return None


def _parse_3gpp_toc_entry(
    line: str,
) -> tuple[str, str] | None:
    """
    Tek bir TOC satırından:

        clause_number,
        clause_title

    çıkarır.
    """

    candidate = (
        line or ""
    ).strip()

    if not candidate:
        return None

    # -------------------------------------------------
    # ANNEX TOC
    # -------------------------------------------------

    annex_match = (
        GPP_ANNEX_TOC_ENTRY.fullmatch(
            candidate
        )
    )

    if annex_match:

        annex_id = (
            annex_match
            .group(1)
            .upper()
        )

        raw_title = (
            annex_match
            .group(2)
            .strip()
        )

        if annex_id.isdigit():

            clause_number = (
                f"ANNEX-{annex_id}"
            )

        else:

            clause_number = (
                annex_id
            )

        title = (
            _clean_3gpp_title(
                raw_title
            )
        )

        if not title:

            title = (
                f"Annex {annex_id}"
            )

        return (
            clause_number,
            title,
        )

    # -------------------------------------------------
    # NORMAL TOC
    # -------------------------------------------------

    normal_match = (
        GPP_TOC_ENTRY.fullmatch(
            candidate
        )
    )

    if not normal_match:
        return None

    clause_number = (
        normal_match
        .group(1)
        .rstrip(".")
    )

    title = (
        _clean_3gpp_title(
            normal_match
            .group(2)
        )
    )

    if not title:
        return None

    # "650 Route des Lucioles ..." benzeri
    # adres gürültüsünü engelle.
    if (
        clause_number.isdigit()
        and "." not in clause_number
    ):

        try:

            if int(
                clause_number
            ) > 99:

                return None

        except ValueError:

            return None

    return (
        clause_number.upper(),
        title,
    )


def _extract_3gpp_toc(
    lines: list[str],
) -> tuple[
    dict[str, str],
    int | None,
    int | None,
]:
    """
    3GPP Contents bölümünden whitelist çıkarır.

    TOC içerisindeki entry'ler çoğunlukla art arda gelir.
    Gerçek içerikte tesadüfen TOC regex'ine benzeyen satırların
    whitelist'e eklenmesini önlemek için ardışıklık kontrolü
    uygulanır.
    """

    toc_start = (
        _find_3gpp_toc_start(
            lines
        )
    )

    if toc_start is None:

        return (
            {},
            None,
            None,
        )

    sections: dict[
        str,
        str,
    ] = {}

    toc_end = toc_start

    scan_end = min(
        len(lines),
        toc_start + 1500,
    )

    i = toc_start + 1

    gap_count = 0
    toc_started = False

    while i < scan_end:

        parsed = (
            _parse_3gpp_toc_entry(
                lines[i]
            )
        )

        if parsed is not None:

            (
                clause_number,
                clause_title,
            ) = parsed

            if (
                clause_number
                not in sections
            ):

                sections[
                    clause_number
                ] = clause_title

            toc_end = i

            toc_started = True
            gap_count = 0

            i += 1
            continue

        if toc_started:

            gap_count += 1

            if gap_count > 6:
                break

        i += 1

    return (
        sections,
        toc_start,
        toc_end,
    )


# =========================================================
# 3GPP TOC POZİSYONLARI
# =========================================================

def _build_3gpp_toc_positions(
    toc_sections: dict[str, str],
) -> dict[str, int]:
    """
    Clause'ların TOC içerisindeki sırasını tutar.

    Recovery sırasında geriye doğru clause eşleşmesini
    engellemek için kullanılır.
    """

    return {
        clause_number: index
        for index, clause_number
        in enumerate(
            toc_sections.keys()
        )
    }


# =========================================================
# 3GPP GERÇEK HEADING MATCH
# =========================================================

def _match_3gpp_heading_against_toc(
    line: str,
    toc_sections: dict[str, str],
) -> tuple[str, str] | None:
    """
    Gerçek içerikteki heading'i TOC whitelist
    üzerinden doğrular.
    """

    if not line:
        return None

    candidate = (
        line.strip()
    )

    if not candidate:
        return None

    # -------------------------------------------------
    # ANNEX ANA BAŞLIĞI
    # -------------------------------------------------

    annex_match = (
        GPP_ANNEX_HEADING.fullmatch(
            candidate
        )
    )

    if annex_match:

        annex_id = (
            annex_match
            .group(1)
            .upper()
        )

        raw_title = (
            annex_match
            .group(2)
            .strip()
        )

        if annex_id.isdigit():

            clause_number = (
                f"ANNEX-{annex_id}"
            )

        else:

            clause_number = (
                annex_id
            )

        expected_title = (
            toc_sections.get(
                clause_number
            )
        )

        if expected_title is None:

            return None

        if raw_title:

            if not _3gpp_titles_match(
                raw_title,
                expected_title,
            ):

                # Annex descriptor extraction farkları
                # nedeniyle clause kimliği burada yeterli.
                pass

        return (
            clause_number,
            expected_title,
        )

    # -------------------------------------------------
    # NORMAL / ANNEX ALT CLAUSE
    # -------------------------------------------------

    heading_match = (
        GPP_SECTION_HEADING.fullmatch(
            candidate
        )
    )

    if not heading_match:
        return None

    clause_number = (
        heading_match
        .group(1)
        .rstrip(".")
        .upper()
    )

    title = (
        _clean_3gpp_title(
            heading_match
            .group(2)
        )
    )

    expected_title = (
        toc_sections.get(
            clause_number
        )
    )

    if expected_title is None:

        return None

    if not _3gpp_titles_match(
        title,
        expected_title,
    ):

        return None

    return (
        clause_number,
        expected_title,
    )


# =========================================================
# 3GPP RECOVERY
# =========================================================

def _match_3gpp_recovered_heading(
    line: str,
    toc_sections: dict[str, str],
    seen_sections: set[str],
    toc_positions: dict[str, int],
    last_toc_position: int,
) -> tuple[
    str,
    str,
    str,
] | None:
    """
    Extraction sırasında clause numarası kaybolmuş
    heading'leri TOC whitelist kullanarak kurtarır.

    İki recovery türü vardır:

    -------------------------------------------------

    TITLE_ONLY

        GPRS attach procedures

    TOC:

        4.1.1 GPRS attach procedures

    -------------------------------------------------

    SUFFIX_NUMBER

        .2 Successful GPRS attach procedures

    TOC:

        4.1.1.2 Successful GPRS attach procedures

    -------------------------------------------------

    Güvenlik kuralları:

    - Clause TOC'da bulunmalıdır.
    - Başlık birebir normalize eşleşmelidir.
    - Clause daha önce görülmemiş olmalıdır.
    - TOC sırası geriye gitmemelidir.
    - Birden fazla olası eşleşme varsa recovery yapılmaz.

    Returns:

        (
            clause_number,
            clause_title,
            recovery_type
        )

    veya None.
    """

    candidate = (
        line or ""
    ).strip()

    if not candidate:
        return None

    # -------------------------------------------------
    # 1. SUFFIX NUMBER RECOVERY
    #
    # .1 Title
    # .2 Title
    # .1.2 Title
    # -------------------------------------------------

    suffix_match = (
        GPP_SUFFIX_HEADING.fullmatch(
            candidate
        )
    )

    if suffix_match:

        suffix = (
            suffix_match
            .group(1)
            .strip()
        )

        candidate_title = (
            _clean_3gpp_title(
                suffix_match
                .group(2)
            )
        )

        possible_matches: list[
            tuple[str, str]
        ] = []

        for (
            clause_number,
            expected_title,
        ) in toc_sections.items():

            if (
                clause_number
                in seen_sections
            ):
                continue

            toc_position = (
                toc_positions.get(
                    clause_number,
                    -1,
                )
            )

            if (
                toc_position
                <= last_toc_position
            ):
                continue

            clause_upper = (
                clause_number.upper()
            )

            if not clause_upper.endswith(
                suffix.upper()
            ):
                continue

            if not _3gpp_titles_match(
                candidate_title,
                expected_title,
            ):
                continue

            possible_matches.append(
                (
                    clause_number,
                    expected_title,
                )
            )

        # Yalnızca tek eşleşme varsa güvenli.
        if len(possible_matches) == 1:

            (
                clause_number,
                clause_title,
            ) = possible_matches[0]

            return (
                clause_number,
                clause_title,
                "suffix_number",
            )

        return None

    # -------------------------------------------------
    # 2. TITLE-ONLY RECOVERY
    #
    # Clause numarası tamamen kaybolmuş.
    #
    # Örnek:
    #
    # GPRS attach procedures
    # -------------------------------------------------

    candidate_title = (
        _clean_3gpp_title(
            candidate
        )
    )

    if not candidate_title:
        return None

    # Aşırı uzun normal cümleleri title olarak
    # değerlendirme ihtimalini azalt.
    if len(candidate_title) > 300:
        return None

    possible_matches: list[
        tuple[str, str]
    ] = []

    for (
        clause_number,
        expected_title,
    ) in toc_sections.items():

        if (
            clause_number
            in seen_sections
        ):
            continue

        toc_position = (
            toc_positions.get(
                clause_number,
                -1,
            )
        )

        if (
            toc_position
            <= last_toc_position
        ):
            continue

        if not _3gpp_titles_match(
            candidate_title,
            expected_title,
        ):
            continue

        possible_matches.append(
            (
                clause_number,
                expected_title,
            )
        )

    # -------------------------------------------------
    # EN KRİTİK GÜVENLİK KURALI
    #
    # "General", "Void", "Introduction" gibi aynı
    # title TOC'da birden fazla clause'a ait olabilir.
    #
    # Tahmin yürütmüyoruz.
    # -------------------------------------------------

    if len(possible_matches) != 1:
        return None

    (
        clause_number,
        clause_title,
    ) = possible_matches[0]

    return (
        clause_number,
        clause_title,
        "title_only",
    )


# =========================================================
# 3GPP İÇERİK BAŞLANGICI
# =========================================================

def _find_3gpp_content_start(
    lines: list[str],
    toc_sections: dict[str, str],
    toc_end: int | None,
) -> int | None:
    """
    TOC bittikten sonra gerçek clause başlangıcını bulur.

    Scope zorunlu değildir.

    Örneğin aşağıdakilerin tümü çalışabilir:

        1 Scope
        1 Scope.
        1. Scope
        0a Scope
        1 Void
        1 Outline of the document
    """

    if not toc_sections:
        return None

    search_start = (
        (
            toc_end + 1
        )
        if toc_end is not None
        else 0
    )

    first_sections = list(
        toc_sections.keys()
    )[:20]

    first_section_set = set(
        first_sections
    )

    for index in range(
        search_start,
        len(lines),
    ):

        heading = (
            _match_3gpp_heading_against_toc(
                line=lines[index],
                toc_sections=toc_sections,
            )
        )

        if heading is None:
            continue

        if (
            heading[0]
            in first_section_set
        ):

            return index

    return None


# =========================================================
# 3GPP FALLBACK
# =========================================================

def _match_3gpp_annex_without_toc(
    line: str,
) -> tuple[str, str] | None:
    """
    TOC bulunmayan ama Annex içeriği bulunan
    doküman parçaları için güvenli fallback.

    Örnek:

        B.1 Coexistence evaluation ...
        B.2 ...
        B.3 ...
    """

    candidate = (
        line or ""
    ).strip()

    if not candidate:
        return None

    match = re.fullmatch(
        r"([A-Z](?:\.\d+)+)"
        r"[ \t]+"
        r"(.+)",
        candidate,
        re.IGNORECASE,
    )

    if not match:
        return None

    return (
        match.group(1).upper(),
        _clean_3gpp_title(
            match.group(2)
        ),
    )


def _split_3gpp_without_toc(
    lines: list[str],
) -> list[
    tuple[str, str, str]
]:
    """
    TOC bulunmayan 3GPP metinleri için kontrollü fallback.

    Burada rastgele numeric heading kabul edilmez.

    Yalnızca Annex-style yapılar işlenir.

    Böylece meeting contribution gibi yanlış fetch edilmiş
    dokümanların:

        1. ...
        2. ...
        3. ...

    satırları yanlışlıkla standart clause'u yapılmaz.
    """

    clauses = []

    current = None

    for line in lines:

        heading = (
            _match_3gpp_annex_without_toc(
                line
            )
        )

        if heading is not None:

            if current:

                clauses.append(
                    current
                )

            current = (
                heading[0],
                heading[1],
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
            "\n".join(
                body
            ).strip(),
        )
        for (
            clause_no,
            clause_title,
            body,
        ) in clauses
    ]


# =========================================================
# 3GPP SPLITTER
# =========================================================

def _split_3gpp_clauses(
    document_text: str,
) -> list[
    tuple[str, str, str]
]:
    """
    3GPP dokümanını clause bazında ayırır.

    Öncelikli yöntem:
        TOC whitelist

    Gerçek içerikte yalnızca TOC'da bulunan
    heading'ler yeni clause başlatır.

    Extraction sırasında bazı heading numaralarının
    kısmen veya tamamen kaybolması ayrı recovery
    adımında ele alınacaktır.
    """

    if not document_text:
        return []

    lines = (
        document_text.splitlines()
    )

    (
        toc_sections,
        _toc_start,
        toc_end,
    ) = (
        _extract_3gpp_toc(
            lines
        )
    )

    # -------------------------------------------------
    # TOC YOKSA
    # -------------------------------------------------

    if not toc_sections:

        return (
            _split_3gpp_without_toc(
                lines
            )
        )

    # -------------------------------------------------
    # GERÇEK İÇERİK BAŞLANGICI
    # -------------------------------------------------

    content_start = (
        _find_3gpp_content_start(
            lines=lines,
            toc_sections=toc_sections,
            toc_end=toc_end,
        )
    )

    if content_start is None:

        content_start = (
            toc_end + 1
            if toc_end is not None
            else 0
        )

    # -------------------------------------------------
    # CLAUSE TOPLAMA
    # -------------------------------------------------

    clauses: list[
        tuple[
            str,
            str,
            list[str],
        ]
    ] = []

    current_clause_no: str | None = None
    current_clause_title: str | None = None
    current_body: list[str] = []

    seen_sections: set[str] = set()

    # -------------------------------------------------
    # CONTENT START'TAN İTİBAREN TARA
    # -------------------------------------------------

    i = content_start

    while i < len(lines):

        line = (
            lines[i]
        )

        # ---------------------------------------------
        # TOC WHITELIST HEADING KONTROLÜ
        # ---------------------------------------------

        heading = (
            _match_3gpp_heading_against_toc(
                line=line,
                toc_sections=toc_sections,
            )
        )

        if heading is not None:

            (
                clause_number,
                clause_title,
            ) = heading

            # Aynı section ikinci kez görülürse
            # yeni clause açma.
            if (
                clause_number
                not in seen_sections
            ):

                # Önce mevcut clause'u kapat.
                if (
                    current_clause_no
                    is not None
                ):

                    clauses.append(
                        (
                            current_clause_no,
                            (
                                current_clause_title
                                or ""
                            ),
                            "\n".join(
                                current_body
                            ).strip(),
                        )
                    )

                # Yeni clause aç.
                current_clause_no = (
                    clause_number
                )

                current_clause_title = (
                    clause_title
                )

                current_body = []

                seen_sections.add(
                    clause_number
                )

                i += 1
                continue

        # ---------------------------------------------
        # MEVCUT CLAUSE BODY
        # ---------------------------------------------

        if (
            current_clause_no
            is not None
        ):

            current_body.append(
                line
            )

        i += 1

    # -------------------------------------------------
    # SON CLAUSE
    # -------------------------------------------------

    if (
        current_clause_no
        is not None
    ):

        clauses.append(
            (
                current_clause_no,
                (
                    current_clause_title
                    or ""
                ),
                "\n".join(
                    current_body
                ).strip(),
            )
        )

    return clauses

# =========================================================
# IETF TABLE OF CONTENTS
# =========================================================

def _find_ietf_toc_start(
    lines: list[str],
) -> int | None:

    for index, line in enumerate(
        lines
    ):

        normalized = (
            line
            .strip()
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

    toc_start = (
        _find_ietf_toc_start(
            lines
        )
    )

    if toc_start is None:

        return (
            {},
            None,
            None,
        )

    sections: dict[
        str,
        str,
    ] = {}

    toc_end = (
        toc_start
    )

    scan_end = min(
        len(lines),
        toc_start + 3000,
    )

    i = (
        toc_start + 1
    )

    last_match_index = (
        toc_start
    )

    while i < scan_end:

        stripped = (
            lines[i].strip()
        )

        if not stripped:

            i += 1
            continue

        # -------------------------------------------------
        # TEK SATIR TOC
        # -------------------------------------------------

        single_match = (
            RFC_TOC_SINGLE_LINE.fullmatch(
                stripped
            )
        )

        if single_match:

            section_number = (
                single_match
                .group(1)
                .strip()
            )

            raw_title = (
                single_match
                .group(2)
                .strip()
            )

            title = (
                _clean_rfc_title(
                    raw_title
                )
            )

            if (
                section_number
                and _looks_like_rfc_toc_title(
                    title
                )
            ):

                if (
                    section_number
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
        # ÇOK SATIRLI TOC
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

            title_lines = []

            j = (
                i + 1
            )

            max_title_end = min(
                len(lines),
                i + 8,
            )

            page_found = False

            while j < max_title_end:

                candidate = (
                    lines[j].strip()
                )

                if not candidate:

                    if (
                        title_lines
                        and j + 1 < max_title_end
                    ):

                        j += 1
                        continue

                    break

                if RFC_PAGE_NUMBER.fullmatch(
                    candidate
                ):

                    combined_title = (
                        " ".join(
                            title_lines
                        )
                    )

                    title = (
                        _clean_rfc_title(
                            combined_title
                        )
                    )

                    if (
                        title_lines
                        and _looks_like_rfc_toc_title(
                            title
                        )
                    ):

                        if (
                            section_number
                            not in sections
                        ):

                            sections[
                                section_number
                            ] = title

                        toc_end = j
                        last_match_index = j

                        page_found = True

                    break

                if (
                    IETF_SECTION_NUMBER.fullmatch(
                        candidate
                    )
                    and title_lines
                ):

                    break

                title_lines.append(
                    candidate
                )

                j += 1

            if page_found:

                i = (
                    j + 1
                )

                continue

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
# IETF HEADING DOĞRULAMA
# =========================================================

def _match_ietf_heading_against_toc(
    lines: list[str],
    index: int,
    toc_sections: dict[str, str],
):

    if index >= len(lines):

        return None

    candidate = (
        lines[index]
        .strip()
    )

    if not candidate:

        return None

    # -------------------------------------------------
    # TEK SATIR
    # -------------------------------------------------

    same_line_match = (
        IETF_SECTION_HEADING.fullmatch(
            candidate
        )
    )

    if same_line_match:

        section_number = (
            same_line_match
            .group(1)
        )

        title = (
            _clean_rfc_title(
                same_line_match
                .group(2)
            )
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
    # -------------------------------------------------

    number_match = (
        IETF_SECTION_NUMBER.fullmatch(
            candidate
        )
    )

    if (
        number_match
        and (
            index + 1
            < len(lines)
        )
    ):

        section_number = (
            number_match
            .group(1)
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
                lines[
                    index + 1
                ]
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


# =========================================================
# IETF İÇERİK BAŞLANGICI
# =========================================================

def _find_ietf_content_start(
    lines: list[str],
    toc_sections: dict[str, str],
    toc_end: int | None,
) -> int | None:

    if not toc_sections:

        return None

    search_start = (
        (
            toc_end + 1
        )
        if toc_end is not None
        else 0
    )

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

        if (
            heading[0]
            in first_section_set
        ):

            return index

    return None


# =========================================================
# IETF FALLBACK HEADING
# =========================================================

def _match_ietf_fallback_heading(
    line: str,
):

    candidate = (
        line.rstrip()
    )

    if not candidate:

        return None

    if (
        candidate
        != candidate.lstrip()
    ):

        return None

    if RFC_TOC_LINE.match(
        candidate
    ):

        return None

    return (
        IETF_SECTION_HEADING.match(
            candidate
        )
    )


# =========================================================
# IETF SPLITTER
# =========================================================

def _split_ietf_clauses(
    document_text: str,
) -> list[
    tuple[str, str, str]
]:

    if not document_text:

        return []

    lines = (
        document_text.splitlines()
    )

    (
        toc_sections,
        _toc_start,
        toc_end,
    ) = (
        _extract_ietf_toc(
            lines
        )
    )

    clauses = []

    current = None

    # -------------------------------------------------
    # TOC VARSA
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
                (
                    toc_end + 1
                )
                if toc_end is not None
                else 0
            )

        i = content_start

        seen_sections = set()

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

                if (
                    section_number
                    not in seen_sections
                ):

                    if current:

                        clauses.append(
                            current
                        )

                    current = (
                        section_number,
                        section_title,
                        [],
                    )

                    seen_sections.add(
                        section_number
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
                "\n".join(
                    body
                ).strip(),
            )
            for (
                clause_no,
                clause_title,
                body,
            ) in clauses
        ]

    # -------------------------------------------------
    # FALLBACK
    # -------------------------------------------------

    for line in lines:

        match = (
            _match_ietf_fallback_heading(
                line
            )
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
            "\n".join(
                body
            ).strip(),
        )
        for (
            clause_no,
            clause_title,
            body,
        ) in clauses
    ]


# =========================================================
# GENERIC SPLITTER
# =========================================================

def _split_generic_clauses(
    document_text: str,
) -> list[
    tuple[str, str, str]
]:

    lines = (
        document_text.splitlines()
    )

    clauses = []

    current = None

    for line in lines:

        candidate = (
            line.rstrip()
        )

        if not candidate:
            continue

        if (
            candidate
            != candidate.lstrip()
        ):

            if current:

                current[2].append(
                    line
                )

            continue

        match = (
            GENERIC_CLAUSE_HEADING.match(
                candidate
            )
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
            "\n".join(
                body
            ).strip(),
        )
        for (
            clause_no,
            clause_title,
            body,
        ) in clauses
    ]


# =========================================================
# ANA CLAUSE SPLITTER
# =========================================================

def split_into_clauses(
    document_text: str,
    doc_org: str,
) -> list[
    tuple[str, str, str]
]:

    if not document_text:

        return []

    org = (
        doc_org
        or ""
    ).strip().upper()

    if org == "IETF":

        return (
            _split_ietf_clauses(
                document_text
            )
        )

    if org == "3GPP":

        return (
            _split_3gpp_clauses(
                document_text
            )
        )

    return (
        _split_generic_clauses(
            document_text
        )
    )


# =========================================================
# UZUN TEXT SPLITTER
# =========================================================

def _split_long_text(
    title: str,
    body: str,
    max_chars: int = MAX_CHUNK_CHARS,
    overlap_chars: int = CHUNK_OVERLAP_CHARS,
) -> list[str]:

    title = (
        title or ""
    ).strip()

    body = (
        body or ""
    ).strip()

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

    if (
        len(
            full_text
        )
        <= max_chars
    ):

        return [
            full_text
        ]

    chunks = []

    title_size = (
        len(title) + 1
        if title
        else 0
    )

    available_body_chars = (
        max_chars
        - title_size
    )

    if (
        available_body_chars
        <= 0
    ):

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

            if (
                candidate_end
                <= start
            ):

                candidate_end = (
                    body.rfind(
                        ". ",
                        search_start,
                        end,
                    )
                )

                if (
                    candidate_end
                    > start
                ):

                    candidate_end += 1

            if (
                candidate_end
                <= start
            ):

                candidate_end = (
                    body.rfind(
                        " ",
                        search_start,
                        end,
                    )
                )

            if (
                candidate_end
                > start
            ):

                end = (
                    candidate_end
                )

        part = (
            body[
                start:end
            ].strip()
        )

        if part:

            if title:

                chunks.append(
                    f"{title}\n{part}"
                )

            else:

                chunks.append(
                    part
                )

        if (
            end
            >= len(body)
        ):

            break

        next_start = max(
            0,
            end - overlap_chars,
        )

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

        if (
            next_start
            <= start
        ):

            next_start = (
                end
            )

        start = (
            next_start
        )

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

    chunks = []

    if not document_text:

        return chunks

    clauses = (
        split_into_clauses(
            document_text=document_text,
            doc_org=doc_org,
        )
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
        # VOID
        # -------------------------------------------------

        is_void = (
            title_clean
            .casefold()
            .startswith(
                "void"
            )
            or (
                body_clean
                .casefold()
                in {
                    "void",
                    "void.",
                }
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
        # NORMAL CHUNK
        # -------------------------------------------------

        text_parts = (
            _split_long_text(
                title=title_clean,
                body=body_clean,
            )
        )

        for text_part in (
            text_parts
        ):

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
