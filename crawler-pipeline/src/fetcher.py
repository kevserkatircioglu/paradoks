"""
Fetches a document from a URL and extracts its text content.

Does NOT persist files to disk long-term -- downloads into memory
(or a temp file, cleaned up after), extracts text, returns the string.

Supports PDF, DOCX, ZIP and plain HTML pages.
"""

import io
import re
import zipfile

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(compatible; standards-crawler/1.0)"
    )
}

TIMEOUT = 30


def fetch_and_read(
    url: str,
) -> str | None:
    """
    URL'deki dokümanı indirir ve metin içeriğini döndürür.

    Desteklenen biçimler:
    - PDF
    - DOCX
    - ZIP içindeki DOCX dosyaları
    - HTML
    """

    try:
        resp = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
        )

    except requests.RequestException:
        return None

    if resp.status_code != 200:
        return None

    content_type = (
        resp.headers.get(
            "Content-Type",
            "",
        ).lower()
    )

    lower_url = (
        url.lower()
    )

    # -----------------------------------------------------
    # PDF
    # -----------------------------------------------------
    if (
        lower_url.endswith(".pdf")
        or "application/pdf"
        in content_type
    ):
        return _read_pdf(
            resp.content
        )

    # -----------------------------------------------------
    # DOCX
    # -----------------------------------------------------
    if (
        lower_url.endswith(".docx")
        or "wordprocessingml"
        in content_type
    ):
        return _read_docx(
            resp.content
        )

    # -----------------------------------------------------
    # ZIP
    # -----------------------------------------------------
    if (
        lower_url.endswith(".zip")
        or "application/zip"
        in content_type
        or "application/x-zip-compressed"
        in content_type
    ):
        return _read_zip(
            resp.content
        )

    # -----------------------------------------------------
    # HTML
    # -----------------------------------------------------
    return _read_html(
        resp.text
    )


def _read_pdf(
    raw_bytes: bytes,
) -> str:
    """
    PDF içeriğini sayfa sayfa okuyarak metne çevirir.
    """

    import pdfplumber

    text_parts: list[str] = []

    with pdfplumber.open(
        io.BytesIO(
            raw_bytes
        )
    ) as pdf:

        for page in pdf.pages:
            text_parts.append(
                page.extract_text()
                or ""
            )

    return "\n".join(
        text_parts
    )


def _read_docx(
    raw_bytes: bytes,
) -> str:
    """
    DOCX dosyasındaki paragraph metinlerini çıkarır.
    """

    import docx

    doc = docx.Document(
        io.BytesIO(
            raw_bytes
        )
    )

    return "\n".join(
        paragraph.text
        for paragraph
        in doc.paragraphs
    )


def _docx_sort_key(
    filename: str,
) -> tuple[int, str]:
    """
    3GPP'nin çok parçalı DOCX paketlerini doğru sıraya dizer.

    Örnek:

    24501-k00_0_cover.docx
    24501-k00_1_Main-Body_s00_s04.docx
    24501-k00_2_Main-Body_s05_s0504.docx
    ...
    24501-k00_6_Annexes_sA_sHistory.docx

    Dosya adındaki _0_, _1_, _2_ gibi sıra numarasını kullanır.
    """

    basename = (
        filename
        .replace("\\", "/")
        .split("/")[-1]
    )

    match = re.search(
        r"_(\d+)_",
        basename,
    )

    if match:
        return (
            int(
                match.group(1)
            ),
            basename.lower(),
        )

    # Sıra numarası olmayan DOCX'ler
    # numaralı parçaların sonuna gider.
    return (
        999999,
        basename.lower(),
    )


def _read_zip(
    raw_bytes: bytes,
) -> str:
    """
    ZIP içindeki TÜM DOCX dosyalarını okur.

    3GPP'nin büyük standartları bazen tek DOCX yerine
    birden fazla Word dosyasına bölünmüş olarak yayınlanır.

    Örneğin TS 24.501:
        0_cover
        1_Main-Body
        2_Main-Body
        ...
        6_Annexes

    Eski davranış yalnızca ilk DOCX'i okuyordu.
    Bu nedenle TS 24.501 gibi çok parçalı standartların
    ana gövdesi kaybolabiliyordu.

    Yeni davranış bütün DOCX parçalarını mantıksal sıraya
    koyar, tek tek okur ve tek bir doküman metni olarak
    birleştirir.
    """

    with zipfile.ZipFile(
        io.BytesIO(
            raw_bytes
        )
    ) as archive:

        docx_names = [
            name
            for name
            in archive.namelist()
            if name.lower().endswith(
                ".docx"
            )
            and not name.startswith(
                "__MACOSX/"
            )
            and not name.split("/")[-1].startswith(
                "~$"
            )
        ]

        if not docx_names:
            return ""

        docx_names.sort(
            key=_docx_sort_key
        )

        text_parts: list[str] = []

        for docx_name in docx_names:
            try:
                with archive.open(
                    docx_name
                ) as file:
                    raw_docx = (
                        file.read()
                    )

                extracted_text = (
                    _read_docx(
                        raw_docx
                    )
                ).strip()

                if not extracted_text:
                    continue

                # Parçalar arasında açık sınır bırakıyoruz.
                # Chunker gerçek clause başlıklarını yine
                # kendi kurallarına göre tespit edecek.
                text_parts.append(
                    extracted_text
                )

            except Exception as error:
                print(
                    "[FETCHER] ZIP içindeki DOCX "
                    "okunamadı:",
                    docx_name,
                    "|",
                    error,
                )

                continue

        return "\n\n".join(
            text_parts
        )


def _read_html(
    html: str,
) -> str:
    """
    HTML sayfasındaki okunabilir metni çıkarır.
    """

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    return soup.get_text(
        separator="\n",
        strip=True,
    )
