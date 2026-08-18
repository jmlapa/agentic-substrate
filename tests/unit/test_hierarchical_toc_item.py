from typing import Any

import pytest
from pydantic import ValidationError

from src.modules.knowledge.domain.value_objects.hierarchical_toc_item import (
    HierarchicalTocItem,
)


def test_create_valid_hierarchical_toc_item() -> None:
    item = HierarchicalTocItem(
        type="section",
        markdown_level="##",
        title="2. Methods",
        page=2,
        parent_section=None,
    )
    assert item.type == "section"
    assert item.markdown_level == "##"
    assert item.title == "2. Methods"
    assert item.page == 2
    assert item.parent_section is None


def test_create_valid_subsection_with_parent() -> None:
    item = HierarchicalTocItem(
        type="subsection",
        markdown_level="###",
        title="2.1 Literature Search",
        page=2,
        parent_section="2. Methods",
    )
    assert item.type == "subsection"
    assert item.markdown_level == "###"
    assert item.parent_section == "2. Methods"


def test_invalid_markdown_level_raises_validation_error() -> None:
    invalid_level: Any = "#####"
    with pytest.raises(ValidationError):
        HierarchicalTocItem(
            type="section",
            markdown_level=invalid_level,  # Not in allowed literals #, ##, ###, ####
            title="Invalid",
            page=1,
        )


def test_hierarchical_toc_item_is_frozen_immutable() -> None:
    item = HierarchicalTocItem(
        type="document_title",
        markdown_level="#",
        title="Paper Title",
        page=1,
    )
    with pytest.raises(ValidationError):
        # Should not allow mutation
        item.title = "New Title"
