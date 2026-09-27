from __future__ import annotations

import base64
import io
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FIXTURES = {
    "attention_is_all_you_need": {
        "title": "Attention Is All You Need",
        "pages": [
            ["Attention Is All You Need", "1 Introduction", "Sequence modeling fixture text."],
            ["2 Model Architecture", "Attention connects queries, keys, and values.", "3 Experiments"],
        ],
    },
    "vision_transformer": {
        "title": "An Image is Worth 16x16 Words",
        "pages": [
            ["An Image is Worth 16x16 Words", "1 Introduction", "Image patch fixture text."],
            ["2 Method", "Patches are mapped to tokens.", "3 Evaluation"],
        ],
    },
}

PNG_1X1_BLUE = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pdf(title: str, pages: list[list[str]]) -> bytes:
    objects: list[bytes] = []
    page_ids = [3 + index * 2 for index in range(len(pages))]
    content_ids = [page_id + 1 for page_id in page_ids]
    font_id = 3 + len(pages) * 2
    info_id = font_id + 1
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode("ascii"))
    for page_id, content_id, lines in zip(page_ids, content_ids, pages):
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>".encode("ascii")
        )
        commands = ["BT", "/F1 18 Tf", "72 720 Td"]
        for index, line in enumerate(lines):
            if index:
                commands.append("0 -36 Td")
            commands.append(f"({pdf_escape(line)}) Tj")
        commands.append("ET")
        stream = "\n".join(commands).encode("ascii")
        objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(f"<< /Title ({pdf_escape(title)}) /Author (Research2Slides fixture) >>".encode("ascii"))

    output = io.BytesIO()
    output.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_id, body in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{object_id} 0 obj\n".encode("ascii"))
        output.write(body)
        output.write(b"\nendobj\n")
    xref = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info {info_id} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    return output.getvalue()


def deterministic_zip(source: Path, target: Path) -> None:
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            info = zipfile.ZipInfo(path.relative_to(source).as_posix(), date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())


def main() -> None:
    raster = ROOT / "vision_transformer" / "source" / "figures" / "patches.png"
    raster.parent.mkdir(parents=True, exist_ok=True)
    raster.write_bytes(PNG_1X1_BLUE)
    for name, fixture in FIXTURES.items():
        root = ROOT / name
        (root / "paper.pdf").write_bytes(make_pdf(fixture["title"], fixture["pages"]))
        deterministic_zip(root / "source", root / "source.zip")
        print(f"built {name}")


if __name__ == "__main__":
    main()

