"""
Protocol Buffer Descriptor Manager for gRPC Transformations.

Manages protobuf descriptors for gRPC services:
- Loads .proto files from disk, inline content, or URLs
- Compiles .proto → .desc using protoc
- Caches compiled descriptors
- Validates proto syntax and file integrity
"""

import hashlib
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

try:
    import requests
except ImportError:
    requests = None  # Optional dependency

from .config import ProtoDescriptor

logger = logging.getLogger(__name__)


class ProtoManager:
    """Protobuf descriptor manager for gRPC transformations.

    Manages Protocol Buffer descriptors for gRPC services. Handles loading
    from files, inline content, or URLs, and compiles .proto files to .desc
    format using protoc.

    Attributes:
        proto_dir: Directory for storing proto files and compiled descriptors
        descriptors: Registry of all loaded ProtoDescriptors

    Examples:
        >>> manager = ProtoManager()
        >>> desc = ProtoDescriptor(name="user_svc", source="file", path="/protos/user.proto")
        >>> manager.register_descriptor(desc)
        >>> loaded = manager.get_descriptor("user_svc")
        >>> loaded.path  # Now points to compiled .desc file
        '/etc/gal/protos/user.desc'

    Thread Safety:
        Not thread-safe. Use in single-threaded context or add external locking.
    """

    def __init__(self, proto_dir: str = "/etc/gal/protos"):
        """Initialize ProtoManager.

        Args:
            proto_dir: Directory to store proto files and compiled descriptors
                      Default: /etc/gal/protos

        Raises:
            OSError: If proto_dir cannot be created due to permissions
        """
        self.proto_dir = Path(proto_dir)
        self.descriptors: Dict[str, ProtoDescriptor] = {}

        try:
            self.proto_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"ProtoManager initialized with directory: {self.proto_dir}")
        except OSError as e:
            logger.error(f"Failed to create proto directory {self.proto_dir}: {e}")
            raise

    def register_descriptor(self, descriptor: ProtoDescriptor) -> None:
        """Register and process a proto descriptor.

        Processes the descriptor based on its source type:
        - file: Validates existence and compiles if .proto
        - inline: Writes content to file and compiles
        - url: Downloads from URL and compiles

        Args:
            descriptor: ProtoDescriptor configuration

        Raises:
            FileNotFoundError: When source="file" and path doesn't exist
            ValueError: When proto syntax is invalid or file extension wrong
            RuntimeError: When protoc compilation fails
            requests.HTTPError: When URL download fails (if source="url")

        Side Effects:
            - May create .proto file in proto_dir (inline/url)
            - Compiles .proto → .desc
            - Updates descriptor.path to point to .desc file
            - Adds descriptor to registry

        Examples:
            >>> manager = ProtoManager()
            >>> desc = ProtoDescriptor(name="svc", source="inline", content="syntax...")
            >>> manager.register_descriptor(desc)
        """
        # Descriptor validation already done in __post_init__
        logger.info(f"Registering proto descriptor: {descriptor.name} (source={descriptor.source})")

        # Check for duplicate names
        if descriptor.name in self.descriptors:
            raise ValueError(
                f"Proto descriptor '{descriptor.name}' is already registered. "
                f"Use unique names for all descriptors."
            )

        if descriptor.source == "file":
            self._validate_file(descriptor)
        elif descriptor.source == "inline":
            self._process_inline(descriptor)
        elif descriptor.source == "url":
            self._process_url(descriptor)

        # Register after successful processing
        self.descriptors[descriptor.name] = descriptor
        logger.info(f"Successfully registered descriptor: {descriptor.name} → {descriptor.path}")

    def get_descriptor(self, name: str) -> Optional[ProtoDescriptor]:
        """Retrieve registered descriptor by name.

        Args:
            name: Descriptor name

        Returns:
            ProtoDescriptor if found, None otherwise

        Examples:
            >>> manager = ProtoManager()
            >>> desc = manager.get_descriptor("user_service")
            >>> if desc:
            ...     print(desc.path)
        """
        return self.descriptors.get(name)

    def list_descriptors(self) -> List[str]:
        """List all registered descriptor names.

        Returns:
            List of descriptor names (sorted alphabetically)

        Examples:
            >>> manager = ProtoManager()
            >>> manager.list_descriptors()
            ['order_service', 'payment_service', 'user_service']
        """
        return sorted(self.descriptors.keys())

    def clear(self) -> None:
        """Clear all registered descriptors.

        Removes all descriptors from the registry. Does NOT delete files
        from disk.

        Examples:
            >>> manager = ProtoManager()
            >>> manager.clear()
            >>> len(manager.descriptors)
            0
        """
        self.descriptors.clear()
        logger.info("Cleared all proto descriptors")

    def _validate_file(self, descriptor: ProtoDescriptor) -> None:
        """Validate file-based descriptor.

        Args:
            descriptor: ProtoDescriptor with source="file"

        Raises:
            FileNotFoundError: If path doesn't exist
            ValueError: If path extension is not .proto or .desc

        Side Effects:
            - If .proto file, compiles to .desc and updates descriptor.path
        """
        path = Path(descriptor.path)

        if not path.exists():
            raise FileNotFoundError(
                f"Proto file not found: {descriptor.path}\n"
                f"Check that the file exists and the path is correct."
            )

        if path.suffix not in [".proto", ".desc"]:
            raise ValueError(
                f"Invalid proto file extension: {path.suffix}\n"
                f"Only .proto and .desc files are supported."
            )

        # If .proto, compile to .desc
        if path.suffix == ".proto":
            logger.info(f"Compiling .proto file: {path}")
            desc_file = self._compile_proto(str(path))
            descriptor.path = str(desc_file)
            logger.info(f"Compiled to: {desc_file}")

    def _process_inline(self, descriptor: ProtoDescriptor) -> None:
        """Process inline proto content.

        Args:
            descriptor: ProtoDescriptor with source="inline"

        Raises:
            RuntimeError: If protoc compilation fails

        Side Effects:
            - Writes .proto file to proto_dir/{name}_{hash}.proto
            - Compiles to .desc
            - Updates descriptor.path
        """
        # Hash content for unique filename (handles content updates)
        content_hash = hashlib.md5(descriptor.content.encode()).hexdigest()[:8]
        proto_file = self.proto_dir / f"{descriptor.name}_{content_hash}.proto"

        logger.info(f"Writing inline proto content to: {proto_file}")

        # Write proto content
        proto_file.write_text(descriptor.content, encoding="utf-8")

        # Compile
        desc_file = self._compile_proto(str(proto_file))
        descriptor.path = str(desc_file)

        logger.info(f"Processed inline proto: {descriptor.name} → {desc_file}")

    def _process_url(self, descriptor: ProtoDescriptor) -> None:
        """Download proto file from URL and compile.

        Args:
            descriptor: ProtoDescriptor with source="url"

        Raises:
            ImportError: If requests library not installed
            requests.HTTPError: If download fails
            RuntimeError: If protoc compilation fails

        Side Effects:
            - Downloads .proto to proto_dir/{name}.proto
            - Compiles to .desc
            - Updates descriptor.path
        """
        if requests is None:
            raise ImportError(
                "requests library is required for URL-based proto descriptors.\n"
                "Install with: pip install requests"
            )

        proto_file = self.proto_dir / f"{descriptor.name}.proto"

        logger.info(f"Downloading proto from URL: {descriptor.url}")

        try:
            # Download with timeout
            response = requests.get(descriptor.url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(
                f"Failed to download proto from {descriptor.url}: {e}\n"
                f"Check URL, network connection, and authentication."
            ) from e

        # Write proto content
        proto_file.write_bytes(response.content)
        logger.info(f"Downloaded to: {proto_file}")

        # Compile
        desc_file = self._compile_proto(str(proto_file))
        descriptor.path = str(desc_file)

        logger.info(f"Processed URL proto: {descriptor.name} → {desc_file}")

    def _compile_proto(self, proto_file: str) -> Path:
        """Compile .proto to .desc using protoc.

        Args:
            proto_file: Path to .proto file

        Returns:
            Path to compiled .desc file

        Raises:
            RuntimeError: If protoc not installed or compilation fails

        Command executed:
            protoc --descriptor_set_out={desc_file} \\
                   --proto_path={proto_dir} \\
                   --include_imports \\
                   {proto_file}
        """
        proto_path = Path(proto_file)
        desc_file = proto_path.with_suffix(".desc")

        # Build protoc command
        cmd = [
            "protoc",
            f"--descriptor_set_out={desc_file}",
            f"--proto_path={self.proto_dir}",
            "--include_imports",  # Include dependencies in descriptor
            str(proto_file),
        ]

        logger.debug(f"Running protoc: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
                cwd=str(self.proto_dir),  # Run in proto_dir for security
            )
        except FileNotFoundError:
            raise RuntimeError(
                "protoc not found. Install Protocol Buffer Compiler:\n"
                "  Ubuntu/Debian: apt-get install protobuf-compiler\n"
                "  MacOS: brew install protobuf\n"
                "  Or download from: https://github.com/protocolbuffers/protobuf/releases"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"protoc compilation timeout for {proto_file}\n"
                f"File may be too large or protoc is hanging."
            )

        if result.returncode != 0:
            raise RuntimeError(
                f"protoc compilation failed for {proto_file}:\n"
                f"Return code: {result.returncode}\n"
                f"Error output:\n{result.stderr}"
            )

        if not desc_file.exists():
            raise RuntimeError(
                f"protoc succeeded but .desc file not created: {desc_file}\n"
                f"This may indicate a protoc bug."
            )

        logger.info(f"Successfully compiled: {proto_file} → {desc_file}")
        return desc_file
