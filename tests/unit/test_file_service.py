"""
Tests for services/file_service.py — FileService
"""


from bantu_os.services.file_service import FileService


class TestFileService:
    def test_read_file(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello bantu os")
        svc = FileService()
        content = svc.read_file(str(test_file))
        assert "hello bantu os" in content

    def test_write_file(self, tmp_path):
        svc = FileService()
        path = tmp_path / "written.txt"
        result = svc.write_file(str(path), "test content")
        assert path.exists()
        assert path.read_text() == "test content"

    def test_delete_file(self, tmp_path):
        test_file = tmp_path / "delete_me.txt"
        test_file.write_text("to be deleted")
        svc = FileService()
        result = svc.delete_file(str(test_file))
        assert not test_file.exists()

    def test_list_directory(self, tmp_path):
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        svc = FileService()
        entries = svc.list_directory(str(tmp_path))
        assert len(entries) == 2

    def test_create_directory(self, tmp_path):
        new_dir = tmp_path / "new_dir"
        svc = FileService()
        result = svc.create_directory(str(new_dir))
        assert new_dir.exists() and new_dir.is_dir()

    def test_copy_file(self, tmp_path):
        src = tmp_path / "source.txt"
        dst = tmp_path / "dest.txt"
        src.write_text("copy me")
        svc = FileService()
        result = svc.copy_file(str(src), str(dst))
        assert dst.exists()
        assert dst.read_text() == "copy me"

    def test_move_file(self, tmp_path):
        src = tmp_path / "old.txt"
        dst = tmp_path / "new.txt"
        src.write_text("move me")
        svc = FileService()
        result = svc.move_file(str(src), str(dst))
        assert not src.exists()
        assert dst.exists()

    def test_get_file_info(self, tmp_path):
        test_file = tmp_path / "info.txt"
        test_file.write_text("info test")
        svc = FileService()
        info = svc.get_file_info(str(test_file))
        assert info["exists"] is True
        assert info["size"] > 0
