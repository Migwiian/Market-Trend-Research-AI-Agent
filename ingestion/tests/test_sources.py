from pathlib import Path

from ingestion.sources import ingest_files, to_snapshot


def test_ingest_files(tmp_path: Path):
    file_path = tmp_path / "sample.txt"
    file_path.write_text("sample content")

    sources = ingest_files(tmp_path)
    assert len(sources) == 1
    assert sources[0].text == "sample content"

    snap = to_snapshot(sources[0])
    assert snap.content_text == "sample content"
    assert snap.snapshot_id.startswith("file:")
