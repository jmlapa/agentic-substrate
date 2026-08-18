import pytest

from src.modules.knowledge.domain.entities.synthetic_document_toc import (
    SyntheticDocumentToc,
)
from src.modules.knowledge.domain.value_objects.hierarchical_toc_item import (
    HierarchicalTocItem,
)


@pytest.fixture
def sample_toc_items() -> list[HierarchicalTocItem]:
    return [
        HierarchicalTocItem(
            type="document_title",
            markdown_level="#",
            title="Maximizing Hypertrophy",
            page=1,
            parent_section=None,
        ),
        HierarchicalTocItem(
            type="section",
            markdown_level="##",
            title="1. Introduction",
            page=1,
            parent_section=None,
        ),
        HierarchicalTocItem(
            type="section",
            markdown_level="##",
            title="2. Methods",
            page=2,
            parent_section=None,
        ),
        HierarchicalTocItem(
            type="subsection",
            markdown_level="###",
            title="2.1 Literature Search",
            page=2,
            parent_section="2. Methods",
        ),
        HierarchicalTocItem(
            type="subsection",
            markdown_level="###",
            title="2.2 Inclusion Criteria",
            page=3,
            parent_section="2. Methods",
        ),
        HierarchicalTocItem(
            type="section",
            markdown_level="##",
            title="3. Discussion",
            page=6,
            parent_section=None,
        ),
    ]


def test_create_synthetic_document_toc(
    sample_toc_items: list[HierarchicalTocItem],
) -> None:
    toc = SyntheticDocumentToc(items=sample_toc_items)
    assert len(toc.items) == 6
    assert toc.total_headings == 6
    assert toc.document_title == "Maximizing Hypertrophy"


def test_get_active_hierarchy_for_page(
    sample_toc_items: list[HierarchicalTocItem],
) -> None:
    toc = SyntheticDocumentToc(items=sample_toc_items)

    # Page 1 -> Document Title + 1. Introduction
    p1_hint = toc.get_active_hierarchy_for_page(1)
    assert "## 1. Introduction" in p1_hint

    # Page 2 -> 2. Methods + 2.1 Literature Search
    p2_hint = toc.get_active_hierarchy_for_page(2)
    assert "## 2. Methods" in p2_hint
    assert "### 2.1 Literature Search" in p2_hint

    # Page 4 (no new heading, should inherit 2.2 Inclusion Criteria)
    p4_hint = toc.get_active_hierarchy_for_page(4)
    assert "## 2. Methods" in p4_hint
    assert "### 2.2 Inclusion Criteria" in p4_hint

    # Page 6 -> 3. Discussion
    p6_hint = toc.get_active_hierarchy_for_page(6)
    assert "## 3. Discussion" in p6_hint


def test_render_markdown_toc(
    sample_toc_items: list[HierarchicalTocItem],
) -> None:
    toc = SyntheticDocumentToc(items=sample_toc_items)
    md_toc = toc.to_markdown_toc()
    assert "# Índice / Table of Contents" in md_toc
    assert "- [1. Introduction]" in md_toc
    assert "  - [2.1 Literature Search]" in md_toc
