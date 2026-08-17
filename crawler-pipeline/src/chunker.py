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


# =========================================================
# CHUNK AYARLARI
# =========================================================

MAX_CHUNK_CHARS = 2400
CHUNK_OVERLAP_CHARS = 300


# =========================================================
# 3GPP / GENERIC CLAUSE
# =========================================================
#
# Örnek:
#
# 9.1.3.4.2 Warning Message Delivery Procedure
# 9.2.15 Void
# =========================================================

GENERIC_CLAUSE_HEADING = re.compile(
    r"^(\d+(?:\.\d+)*)[ \t]+(.+)$"
)


# =========================================================
# IETF / RFC TEK SATIR HEADING
# =========================================================
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
# İlk section numarası 1-99 ile sınırlandırılır.
#
# Böylece:
#
# 200 OK
# 488 Not Acceptable Here
# 5061 ...
#
# gibi değerlerin section sanılması azaltılır.
# =========================================================

IETF_SECTION_HEADING = re.compile(
    r"^([1-9]\d?(?:\.\d+)*)\.?[ \t]+(.+)$"
)


# =========================================================
# IETF / RFC SADECE SECTION NUMARASI
# =========================================================
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
# =========================================================

IETF_SECTION_NUMBER = re.compile(
    r"^([1-9]\d?(?:\.\d+)*)\.?$"
)


# =========================================================
# RFC TABLE OF CONTENTS - TEK SATIR
# =========================================================
#
# Her iki biçimi de destekler:
#
# 10.2.1.2 Preferences among Contact Addresses ...... 61
#
# ve:
#
# 10.2.1.1   Setting the Expiration Interval
#            of Contact Addresses                    60
#
# Tek satırda title + page olduğunda noktalı lider
# bulunması ZORUNLU DEĞİLDİR.
#
# Kritik RFC 3261 örneği:
#
# 10.2.1.1   Setting the Expiration Interval of Contact Addresses    60
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


# =========================================================
# RFC TOC - NOKTALI LİDERLİ SATIR KONTROLÜ
# =========================================================
#
# Fallback kontrollerinde kullanılır.
#
# Örnek:
#
# 10.2.1.2 Preferences among Contact Addresses ...... 61
# =========================================================

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


# =========================================================
# RFC TOC PAGE NUMBER
# =========================================================
#
# Split edilmiş TOC örneği:
#
# 13.2.1
# Creating the Initial INVITE ....................
# 78
# =========================================================

RFC_PAGE_NUMBER = re.compile(
    r"^\d{1,4}$"
)


# =========================================================
# 3GPP TABLE OF CONTENTS
# =========================================================
#
# Örnek:
#
# 9.1.3.4.2    Warning Message Delivery Procedure    27
#
# Son sayı sayfa numarasıdır.
# =========================================================

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
    Birden fazla whitespace karakterini
    tek boşluğa indirger.
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

    Örnek:

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

    # -------------------------------------------------
    # RFC 6733 benzeri extraction:
    #
    # .  Introduction
    #
    # başındaki tek noktayı temizle.
    # -------------------------------------------------

    value = re.sub(
        r"^\.\s*",
        "",
        value,
    )

    # -------------------------------------------------
    # TOC dot leader temizliği:
    #
    # Introduction ........................
    # -------------------------------------------------

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
    """
    TOC'dan çıkarılan başlığın makul olup olmadığını
    kaba şekilde kontrol eder.

    Amaç, yalnızca bir sayı veya anlamsız extraction
    parçasının TOC entry olarak kabul edilmesini azaltmaktır.
    """

    cleaned = _clean_rfc_title(
        title
    )

    if not cleaned:
        return False

    # Sadece sayı / section benzeri bir değer olmasın.
    if re.fullmatch(
        r"\d+(?:\.\d+)*\.?",
        cleaned,
    ):
        return False

    # En az bir alfabetik karakter içersin.
    if not re.search(
        r"[A-Za-z]",
        cleaned,
    ):
        return False

    return True


# =========================================================
# IETF TABLE OF CONTENTS
# =========================================================

def _find_ietf_toc_start(
    lines: list[str],
) -> int | None:
    """
    RFC içerisindeki Table of Contents başlangıcını bulur.
    """

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
    """
    RFC Table of Contents içerisinden:

        section_number -> section_title

    haritasını çıkarır.

    Desteklenen formatlar:

    -------------------------------------------------------

    FORMAT 1:

        13.2.1 Creating the Initial INVITE ........ 78

    -------------------------------------------------------

    FORMAT 2:

        10.2.1.1   Setting the Expiration Interval
                   of Contact Addresses             60

    Tek satıra extraction edilmiş hâli:

        10.2.1.1   Setting the Expiration Interval
        of Contact Addresses    60

    veya doğrudan:

        10.2.1.1   Setting the Expiration Interval
                   of Contact Addresses    60

    -------------------------------------------------------

    FORMAT 3:

        13.2.1
        Creating the Initial INVITE ............
        78

    -------------------------------------------------------

    FORMAT 4:

        1
        . Introduction .........................
        7

    -------------------------------------------------------

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

    # RFC TOC'ları normalde dokümanın başındadır.
    # Yine de büyük RFC'ler için geniş bir pencere
    # bırakıyoruz.
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
        # FORMAT 1 / FORMAT 2
        #
        # Tek satır TOC entry.
        #
        # Noktalı lider ZORUNLU DEĞİL.
        #
        # Örnek:
        #
        # 10.2.1.2 Preferences ............... 61
        #
        # veya:
        #
        # 10.2.1.1   Setting the Expiration
        #             Interval ...             60
        #
        # extraction sonrası tek satırsa:
        #
        # 10.2.1.1 Setting the Expiration Interval ... 60
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
        # FORMAT 3 / FORMAT 4
        #
        # Çok satırlı extraction:
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

            title_lines: list[
                str
            ] = []

            j = (
                i + 1
            )

            # Başlık extraction sırasında birkaç satıra
            # bölünebilir.
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

                    # Arada tek boş satır varsa tamamen
                    # vazgeçmeden bir sonraki satırı dene.
                    if (
                        title_lines
                        and j + 1 < max_title_end
                    ):
                        j += 1
                        continue

                    break

                # -----------------------------------------
                # Son satır sadece sayfa numarasıysa
                # TOC entry tamamlanmıştır.
                # -----------------------------------------

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

                    # Eski sürümde burada:
                    #
                    # ".." in combined_title
                    #
                    # zorunluydu.
                    #
                    # Artık DEĞİL.
                    #
                    # Çünkü RFC 3261:
                    #
                    # 10.2.1.1 Setting the Expiration ...
                    #
                    # satırında dot leader bulunmuyor.
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

                # -----------------------------------------
                # Eğer hemen başka section numarası geldiyse
                # mevcut entry geçerli değildir.
                # -----------------------------------------

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

        # -------------------------------------------------
        # TOC SONU
        #
        # Son başarılı TOC entry'den sonra uzun süre
        # yeni entry gelmiyorsa gerçek içerik başlamış
        # kabul edilir.
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
# IETF GERÇEK HEADING DOĞRULAMA
# =========================================================

def _match_ietf_heading_against_toc(
    lines: list[str],
    index: int,
    toc_sections: dict[str, str],
):
    """
    Verilen satırın gerçek RFC section heading olup
    olmadığını TOC whitelist kullanarak kontrol eder.

    Desteklenen biçimler:

        1 Introduction

        1. Introduction

        1
        Introduction

        1
        . Introduction

    Returns:

        (
            section_number,
            title,
            consumed_lines
        )

    veya:

        None
    """

    if index >= len(lines):

        return None

    raw = (
        lines[index]
    )

    candidate = (
        raw.strip()
    )

    if not candidate:

        return None

    # -------------------------------------------------
    # TEK SATIR HEADING
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
            expected_title
            is not None
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
    # İKİ SATIR HEADING
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
# IETF GERÇEK İÇERİK BAŞLANGICI
# =========================================================

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
        (
            toc_end + 1
        )
        if toc_end is not None
        else 0
    )

    # İlk birkaç section üzerinden içerik başlangıcını
    # tespit ediyoruz.
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

        section_number = (
            heading[0]
        )

        if (
            section_number
            in first_section_set
        ):

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

    Böylece metin içerisindeki:

        Section 8.1.1
        20.15
        17.2.3

    gibi section referanslarının yanlışlıkla gerçek
    heading kabul edilmesi engellenir.
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
        _extract_ietf_toc(
            lines
        )
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
    # TOC BULUNDUYSA GÜVENLİ PARSER
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

        i = (
            content_start
        )

        seen_sections: set[
            str
        ] = set()

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

                # Gerçek section aynı RFC içinde normalde
                # ikinci kez başlamamalıdır.
                #
                # TOC whitelist zaten güçlü filtre sağlar,
                # bu ek kontrol içerikte tekrar görülen
                # başlıklara karşı güvenlik sağlar.
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
    #
    # Bazı RFC'lerde Table of Contents olmayabilir.
    #
    # Bu durumda eski tek-satır heading davranışı
    # korunur.
    # -------------------------------------------------

    for line in lines:

        match = (
            _match_heading(
                line=line,
                doc_org="IETF",
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

    candidate = (
        line.rstrip()
    )

    if not candidate:

        return None

    # Girintili örnek satırlarını heading olarak
    # değerlendirme.
    if (
        candidate
        != candidate.lstrip()
    ):

        return None

    org = (
        doc_org
        or ""
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

                if (
                    int(
                        clause_number
                    )
                    > 99
                ):

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

    if not document_text:

        return []

    org = (
        doc_org
        or ""
    ).strip().upper()

    # -------------------------------------------------
    # IETF
    #
    # RFC'ler için özel TOC tabanlı parser.
    # -------------------------------------------------

    if org == "IETF":

        return (
            _split_ietf_clauses(
                document_text
            )
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
        # 3GPP GERÇEK İÇERİK BAŞLANGICI
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
                and (
                    scope_match.group(1)
                    == "1"
                )
                and (
                    scope_match
                    .group(2)
                    .strip()
                    .lower()
                    == "scope"
                )
            ):

                gpp_content_started = (
                    True
                )

            else:

                continue

        # -------------------------------------------------
        # 3GPP TOC TEMİZLİĞİ
        # -------------------------------------------------

        if org == "3GPP":

            if GPP_TOC_LINE.match(
                line.strip()
            ):

                continue

        # -------------------------------------------------
        # HEADING EŞLEŞMESİ
        # -------------------------------------------------

        match = (
            _match_heading(
                line=line,
                doc_org=doc_org,
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

    title = (
        title.strip()
    )

    body = (
        body.strip()
    )

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

    # -------------------------------------------------
    # Zaten yeterince küçükse bölme.
    # -------------------------------------------------

    if (
        len(
            full_text
        )
        <= max_chars
    ):

        return [
            full_text
        ]

    chunks: list[
        str
    ] = []

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

                chunk_text = (
                    f"{title}\n{part}"
                )

            else:

                chunk_text = (
                    part
                )

            chunks.append(
                chunk_text
            )

        if (
            end
            >= len(body)
        ):

            break

        # -------------------------------------------------
        # OVERLAP
        # -------------------------------------------------

        next_start = max(
            0,
            end
            - overlap_chars,
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
                next_space
                != -1
                and (
                    next_space
                    < end
                )
            ):

                next_start = (
                    next_space
                    + 1
                )

        # Sonsuz döngü koruması.
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
        # VOID KONTROLÜ
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
        # NORMAL / UZUN CLAUSE CHUNKING
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
