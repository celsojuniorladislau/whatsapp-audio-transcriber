from whatsapp_transcriber.repository import SQLiteRepository


def test_repository_records_and_updates_message(tmp_path) -> None:
    repository = SQLiteRepository(str(tmp_path / "messages.sqlite3"))
    repository.initialize()

    assert repository.has_message("wamid-1") is False
    repository.mark_message("wamid-1", "processing")
    assert repository.has_message("wamid-1") is True
    repository.mark_message("wamid-1", "done")

    assert repository.get_status("wamid-1") == "done"


def test_repository_records_error_without_duplicate_rows(tmp_path) -> None:
    repository = SQLiteRepository(str(tmp_path / "messages.sqlite3"))
    repository.initialize()
    repository.mark_message("wamid-2", "processing")
    repository.mark_message("wamid-2", "error", "provider unavailable")

    assert repository.get_status("wamid-2") == "error"
    assert repository.get_error("wamid-2") == "provider unavailable"
