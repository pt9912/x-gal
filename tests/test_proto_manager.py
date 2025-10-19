"""
Tests for ProtoManager (Protocol Buffer descriptor management).

Tests proto descriptor registration, compilation, retrieval, and error handling
for file-based, inline, and URL-based proto sources.
"""

import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from gal.config import ProtoDescriptor
from gal.proto_manager import ProtoManager


@pytest.fixture
def temp_proto_dir():
    """Create temporary directory for proto files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def proto_manager(temp_proto_dir):
    """Create ProtoManager with temporary directory."""
    return ProtoManager(proto_dir=temp_proto_dir)


@pytest.fixture
def sample_proto_content():
    """Sample valid proto3 content."""
    return '''
syntax = "proto3";
package user.v1;

message User {
    string id = 1;
    string name = 2;
    string email = 3;
}

service UserService {
    rpc GetUser (GetUserRequest) returns (GetUserResponse);
}

message GetUserRequest {
    string user_id = 1;
}

message GetUserResponse {
    User user = 1;
}
'''


class TestProtoManagerInit:
    """Tests for ProtoManager initialization."""

    def test_proto_manager_init_default(self):
        """Test ProtoManager with default directory."""
        # Mock mkdir to avoid permission issues
        with patch.object(Path, 'mkdir'):
            manager = ProtoManager()
            assert manager.proto_dir == Path("/etc/gal/protos")
            assert manager.descriptors == {}

    def test_proto_manager_init_custom_dir(self, temp_proto_dir):
        """Test ProtoManager with custom directory."""
        manager = ProtoManager(proto_dir=temp_proto_dir)
        assert manager.proto_dir == Path(temp_proto_dir)
        assert manager.descriptors == {}
        assert manager.proto_dir.exists()


class TestProtoManagerFileDescriptor:
    """Tests for file-based proto descriptors."""

    def test_register_descriptor_file_desc(self, proto_manager, temp_proto_dir):
        """Test registering .desc file (no compilation needed)."""
        # Create a fake .desc file
        desc_file = Path(temp_proto_dir) / "user.desc"
        desc_file.write_bytes(b"fake descriptor content")

        descriptor = ProtoDescriptor(
            name="user_service",
            source="file",
            path=str(desc_file)
        )

        proto_manager.register_descriptor(descriptor)

        assert "user_service" in proto_manager.descriptors
        registered = proto_manager.get_descriptor("user_service")
        assert registered is not None
        assert registered.path == str(desc_file)

    def test_register_descriptor_file_proto_with_mock(self, proto_manager, temp_proto_dir, sample_proto_content):
        """Test registering .proto file with mocked protoc compilation."""
        # Create a real .proto file
        proto_file = Path(temp_proto_dir) / "user.proto"
        proto_file.write_text(sample_proto_content, encoding="utf-8")

        descriptor = ProtoDescriptor(
            name="user_service",
            source="file",
            path=str(proto_file)
        )

        # Mock _compile_proto to avoid needing real protoc
        desc_file = Path(temp_proto_dir) / "user.desc"
        with patch.object(proto_manager, '_compile_proto', return_value=desc_file):
            proto_manager.register_descriptor(descriptor)

        assert "user_service" in proto_manager.descriptors
        registered = proto_manager.get_descriptor("user_service")
        assert registered is not None
        assert registered.path == str(desc_file)

    def test_register_descriptor_file_not_found(self, proto_manager):
        """Test registering non-existent file raises FileNotFoundError."""
        descriptor = ProtoDescriptor(
            name="user_service",
            source="file",
            path="/nonexistent/user.proto"
        )

        with pytest.raises(FileNotFoundError, match="Proto file not found"):
            proto_manager.register_descriptor(descriptor)

    def test_register_descriptor_file_invalid_extension(self, proto_manager, temp_proto_dir):
        """Test registering file with invalid extension raises ValueError."""
        # Create file with wrong extension
        invalid_file = Path(temp_proto_dir) / "user.txt"
        invalid_file.write_text("content", encoding="utf-8")

        descriptor = ProtoDescriptor(
            name="user_service",
            source="file",
            path=str(invalid_file)
        )

        with pytest.raises(ValueError, match="Invalid proto file extension"):
            proto_manager.register_descriptor(descriptor)


class TestProtoManagerInlineDescriptor:
    """Tests for inline proto descriptors."""

    def test_register_descriptor_inline(self, proto_manager, temp_proto_dir, sample_proto_content):
        """Test registering inline proto content."""
        descriptor = ProtoDescriptor(
            name="user_service",
            source="inline",
            content=sample_proto_content
        )

        # Mock _compile_proto
        content_hash = hashlib.md5(sample_proto_content.encode()).hexdigest()[:8]
        expected_proto_file = Path(temp_proto_dir) / f"user_service_{content_hash}.proto"
        expected_desc_file = Path(temp_proto_dir) / f"user_service_{content_hash}.desc"

        with patch.object(proto_manager, '_compile_proto', return_value=expected_desc_file):
            proto_manager.register_descriptor(descriptor)

        # Check proto file was written
        assert expected_proto_file.exists()
        assert expected_proto_file.read_text(encoding="utf-8") == sample_proto_content

        # Check descriptor was registered
        assert "user_service" in proto_manager.descriptors
        registered = proto_manager.get_descriptor("user_service")
        assert registered.path == str(expected_desc_file)

    def test_register_descriptor_inline_content_hash(self, proto_manager, temp_proto_dir):
        """Test inline descriptor creates unique filenames based on content hash."""
        content1 = 'syntax = "proto3"; package test.v1;'
        content2 = 'syntax = "proto3"; package test.v2;'

        desc1 = ProtoDescriptor(name="test1", source="inline", content=content1)
        desc2 = ProtoDescriptor(name="test2", source="inline", content=content2)

        hash1 = hashlib.md5(content1.encode()).hexdigest()[:8]
        hash2 = hashlib.md5(content2.encode()).hexdigest()[:8]

        desc_file1 = Path(temp_proto_dir) / f"test1_{hash1}.desc"
        desc_file2 = Path(temp_proto_dir) / f"test2_{hash2}.desc"

        with patch.object(proto_manager, '_compile_proto', side_effect=[desc_file1, desc_file2]):
            proto_manager.register_descriptor(desc1)
            proto_manager.register_descriptor(desc2)

        # Files should have different hashes
        proto_file1 = Path(temp_proto_dir) / f"test1_{hash1}.proto"
        proto_file2 = Path(temp_proto_dir) / f"test2_{hash2}.proto"

        assert proto_file1.exists()
        assert proto_file2.exists()
        assert hash1 != hash2


class TestProtoManagerURLDescriptor:
    """Tests for URL-based proto descriptors."""

    def test_register_descriptor_url(self, proto_manager, temp_proto_dir, sample_proto_content):
        """Test registering proto from URL."""
        descriptor = ProtoDescriptor(
            name="user_service",
            source="url",
            url="https://api.example.com/protos/user.proto"
        )

        # Mock requests.get
        mock_response = Mock()
        mock_response.content = sample_proto_content.encode("utf-8")
        mock_response.raise_for_status = Mock()

        expected_desc_file = Path(temp_proto_dir) / "user_service.desc"

        with patch('gal.proto_manager.requests') as mock_requests:
            mock_requests.get.return_value = mock_response
            with patch.object(proto_manager, '_compile_proto', return_value=expected_desc_file):
                proto_manager.register_descriptor(descriptor)

        # Check requests.get was called
        mock_requests.get.assert_called_once_with(
            "https://api.example.com/protos/user.proto",
            timeout=30
        )

        # Check proto file was written
        proto_file = Path(temp_proto_dir) / "user_service.proto"
        assert proto_file.exists()

        # Check descriptor was registered
        assert "user_service" in proto_manager.descriptors
        registered = proto_manager.get_descriptor("user_service")
        assert registered.path == str(expected_desc_file)

    def test_register_descriptor_url_without_requests(self, proto_manager):
        """Test URL descriptor without requests library raises ImportError."""
        descriptor = ProtoDescriptor(
            name="user_service",
            source="url",
            url="https://api.example.com/protos/user.proto"
        )

        # Mock requests as None (not installed)
        with patch('gal.proto_manager.requests', None):
            with pytest.raises(ImportError, match="requests library is required"):
                proto_manager.register_descriptor(descriptor)

    def test_register_descriptor_url_download_failure(self, proto_manager):
        """Test URL download failure raises RuntimeError."""
        descriptor = ProtoDescriptor(
            name="user_service",
            source="url",
            url="https://api.example.com/protos/user.proto"
        )

        # Mock requests to raise exception
        with patch('gal.proto_manager.requests') as mock_requests:
            mock_requests.get.side_effect = Exception("Connection error")
            mock_requests.RequestException = Exception

            with pytest.raises(RuntimeError, match="Failed to download proto"):
                proto_manager.register_descriptor(descriptor)


class TestProtoManagerRetrieval:
    """Tests for descriptor retrieval."""

    def test_get_descriptor_found(self, proto_manager, temp_proto_dir):
        """Test get_descriptor returns registered descriptor."""
        desc_file = Path(temp_proto_dir) / "user.desc"
        desc_file.write_bytes(b"fake content")

        descriptor = ProtoDescriptor(name="user_svc", source="file", path=str(desc_file))
        proto_manager.register_descriptor(descriptor)

        result = proto_manager.get_descriptor("user_svc")
        assert result is not None
        assert result.name == "user_svc"
        assert result.path == str(desc_file)

    def test_get_descriptor_not_found(self, proto_manager):
        """Test get_descriptor returns None for non-existent descriptor."""
        result = proto_manager.get_descriptor("nonexistent")
        assert result is None

    def test_list_descriptors(self, proto_manager, temp_proto_dir):
        """Test list_descriptors returns sorted list of names."""
        # Create multiple .desc files
        desc1 = Path(temp_proto_dir) / "user.desc"
        desc2 = Path(temp_proto_dir) / "order.desc"
        desc3 = Path(temp_proto_dir) / "payment.desc"

        desc1.write_bytes(b"content1")
        desc2.write_bytes(b"content2")
        desc3.write_bytes(b"content3")

        # Register in random order
        proto_manager.register_descriptor(ProtoDescriptor(name="payment_svc", source="file", path=str(desc3)))
        proto_manager.register_descriptor(ProtoDescriptor(name="user_svc", source="file", path=str(desc1)))
        proto_manager.register_descriptor(ProtoDescriptor(name="order_svc", source="file", path=str(desc2)))

        # Should return sorted
        result = proto_manager.list_descriptors()
        assert result == ["order_svc", "payment_svc", "user_svc"]

    def test_list_descriptors_empty(self, proto_manager):
        """Test list_descriptors returns empty list when no descriptors."""
        result = proto_manager.list_descriptors()
        assert result == []


class TestProtoManagerClear:
    """Tests for clear functionality."""

    def test_clear(self, proto_manager, temp_proto_dir):
        """Test clear removes all descriptors from registry."""
        desc_file = Path(temp_proto_dir) / "user.desc"
        desc_file.write_bytes(b"content")

        descriptor = ProtoDescriptor(name="user_svc", source="file", path=str(desc_file))
        proto_manager.register_descriptor(descriptor)

        assert len(proto_manager.descriptors) == 1

        proto_manager.clear()

        assert len(proto_manager.descriptors) == 0
        assert proto_manager.list_descriptors() == []

        # File should still exist on disk
        assert desc_file.exists()


class TestProtoManagerEdgeCases:
    """Tests for edge cases and error handling."""

    def test_register_duplicate_descriptor(self, proto_manager, temp_proto_dir):
        """Test registering duplicate descriptor name raises ValueError."""
        desc_file = Path(temp_proto_dir) / "user.desc"
        desc_file.write_bytes(b"content")

        descriptor1 = ProtoDescriptor(name="user_svc", source="file", path=str(desc_file))
        proto_manager.register_descriptor(descriptor1)

        # Try to register with same name
        descriptor2 = ProtoDescriptor(name="user_svc", source="file", path=str(desc_file))

        with pytest.raises(ValueError, match="already registered"):
            proto_manager.register_descriptor(descriptor2)

    def test_compile_proto_missing_protoc(self, proto_manager, temp_proto_dir, sample_proto_content):
        """Test compilation fails gracefully when protoc not installed."""
        proto_file = Path(temp_proto_dir) / "user.proto"
        proto_file.write_text(sample_proto_content, encoding="utf-8")

        # Mock subprocess.run to raise FileNotFoundError
        with patch('subprocess.run', side_effect=FileNotFoundError("protoc not found")):
            with pytest.raises(RuntimeError, match="protoc not found"):
                proto_manager._compile_proto(str(proto_file))

    def test_compile_proto_syntax_error(self, proto_manager, temp_proto_dir):
        """Test compilation fails with invalid proto syntax."""
        # Create proto file with syntax error
        proto_file = Path(temp_proto_dir) / "invalid.proto"
        proto_file.write_text("invalid proto syntax!", encoding="utf-8")

        # Mock subprocess.run to return error
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "syntax error at line 1"

        with patch('subprocess.run', return_value=mock_result):
            with pytest.raises(RuntimeError, match="protoc compilation failed"):
                proto_manager._compile_proto(str(proto_file))

    def test_compile_proto_timeout(self, proto_manager, temp_proto_dir, sample_proto_content):
        """Test compilation timeout raises RuntimeError."""
        proto_file = Path(temp_proto_dir) / "user.proto"
        proto_file.write_text(sample_proto_content, encoding="utf-8")

        # Mock subprocess.run to raise TimeoutExpired
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired("protoc", 30)):
            with pytest.raises(RuntimeError, match="timeout"):
                proto_manager._compile_proto(str(proto_file))

    def test_compile_proto_desc_not_created(self, proto_manager, temp_proto_dir, sample_proto_content):
        """Test error when protoc succeeds but .desc file not created."""
        proto_file = Path(temp_proto_dir) / "user.proto"
        proto_file.write_text(sample_proto_content, encoding="utf-8")

        # Mock subprocess.run to succeed but not create .desc file
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch('subprocess.run', return_value=mock_result):
            with pytest.raises(RuntimeError, match=".desc file not created"):
                proto_manager._compile_proto(str(proto_file))
