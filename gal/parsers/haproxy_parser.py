"""HAProxy Configuration Parser.

Parses HAProxy haproxy.cfg files into structured sections
for conversion to GAL.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SectionType(Enum):
    """HAProxy configuration section types."""

    GLOBAL = "global"
    DEFAULTS = "defaults"
    FRONTEND = "frontend"
    BACKEND = "backend"
    LISTEN = "listen"


@dataclass
class HAProxySection:
    """Represents a HAProxy configuration section."""

    type: SectionType
    name: Optional[str]  # None for global/defaults
    directives: List[Dict[str, Any]] = field(default_factory=list)


class HAProxyConfigParser:
    """Parser for haproxy.cfg files.

    Parses HAProxy configuration files into structured sections
    for conversion to GAL.

    Example:
        >>> parser = HAProxyConfigParser()
        >>> sections = parser.parse(config_text)
        >>> for section in sections:
        ...     print(f"{section.type}: {section.name}")
    """

    def __init__(self):
        self.lines = []
        self.pos = 0

    def parse(self, config_text: str) -> List[HAProxySection]:
        """Parse haproxy.cfg into sections.

        Args:
            config_text: haproxy.cfg content

        Returns:
            List of HAProxySection objects

        Raises:
            ValueError: If syntax is invalid
        """
        if not config_text or not config_text.strip():
            raise ValueError("Empty configuration")

        # Preprocess
        lines = self._preprocess(config_text)
        self.lines = lines
        self.pos = 0

        sections = []
        current_section = None

        while self.pos < len(self.lines):
            line = self.lines[self.pos].strip()

            if not line:
                self.pos += 1
                continue

            # Check for section start
            if line.startswith("global"):
                if current_section:
                    sections.append(current_section)
                current_section = HAProxySection(type=SectionType.GLOBAL, name=None, directives=[])
                self.pos += 1

            elif line.startswith("defaults"):
                if current_section:
                    sections.append(current_section)
                current_section = HAProxySection(
                    type=SectionType.DEFAULTS, name=None, directives=[]
                )
                self.pos += 1

            elif line.startswith("frontend"):
                if current_section:
                    sections.append(current_section)
                parts = line.split(maxsplit=1)
                name = parts[1] if len(parts) > 1 else "unnamed"
                current_section = HAProxySection(
                    type=SectionType.FRONTEND, name=name, directives=[]
                )
                self.pos += 1

            elif line.startswith("backend"):
                if current_section:
                    sections.append(current_section)
                parts = line.split(maxsplit=1)
                name = parts[1] if len(parts) > 1 else "unnamed"
                current_section = HAProxySection(type=SectionType.BACKEND, name=name, directives=[])
                self.pos += 1

            elif line.startswith("listen"):
                if current_section:
                    sections.append(current_section)
                parts = line.split(maxsplit=1)
                name = parts[1] if len(parts) > 1 else "unnamed"
                current_section = HAProxySection(type=SectionType.LISTEN, name=name, directives=[])
                self.pos += 1

            else:
                # Directive within current section
                if current_section:
                    directive = self._parse_directive(line)
                    if directive:
                        current_section.directives.append(directive)
                self.pos += 1

        # Append last section
        if current_section:
            sections.append(current_section)

        return sections

    def _preprocess(self, config_text: str) -> List[str]:
        """Preprocess config: remove comments, handle multi-line.

        Args:
            config_text: Raw haproxy.cfg content

        Returns:
            List of processed lines
        """
        lines = []

        for line in config_text.split("\n"):
            # Remove comments
            if "#" in line:
                line = line[: line.index("#")]

            line = line.strip()

            # Handle line continuation (backslash at end)
            if line.endswith("\\"):
                # Multi-line directive - combine with next line
                # For simplicity, we'll strip the backslash
                line = line[:-1].strip()

            if line:
                lines.append(line)

        return lines

    def _parse_directive(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single directive line.

        Args:
            line: Directive line

        Returns:
            Dict with 'name' and 'value', or None if invalid
        """
        parts = line.split(maxsplit=1)

        if not parts:
            return None

        directive_name = parts[0]
        directive_value = parts[1] if len(parts) > 1 else ""

        return {"name": directive_name, "value": directive_value}

    def get_sections_by_type(
        self, sections: List[HAProxySection], section_type: SectionType
    ) -> List[HAProxySection]:
        """Get all sections of a specific type.

        Args:
            sections: List of all sections
            section_type: Type to filter by

        Returns:
            List of sections matching the type
        """
        return [s for s in sections if s.type == section_type]

    def find_directive(
        self, section: HAProxySection, directive_name: str
    ) -> Optional[Dict[str, Any]]:
        """Find first directive with given name in section.

        Args:
            section: Section to search in
            directive_name: Name of directive to find

        Returns:
            Directive dict or None if not found
        """
        for directive in section.directives:
            if directive["name"] == directive_name:
                return directive
        return None

    def find_all_directives(
        self, section: HAProxySection, directive_name: str
    ) -> List[Dict[str, Any]]:
        """Find all directives with given name in section.

        Args:
            section: Section to search in
            directive_name: Name of directive to find

        Returns:
            List of matching directives
        """
        return [d for d in section.directives if d["name"] == directive_name]
