from src.core.image_assets import parse_markdown_image_reference
from src.core.markdown_project_parser import MarkdownProjectParser
from src.core.models import ElementType


def test_image_reference_supports_balanced_parentheses_and_title() -> None:
    raw = (
        "![CPO chart](./Co_Packaged_Optics_(CPO)_images/img_098.png "
        '"Bandwidth chart")'
    )

    reference = parse_markdown_image_reference(raw)

    assert reference is not None
    assert reference.source == "./Co_Packaged_Optics_(CPO)_images/img_098.png"
    assert reference.alt == "CPO chart"
    assert reference.title == "Bandwidth chart"


def test_parser_stores_image_path_instead_of_entire_markdown_token() -> None:
    parser = MarkdownProjectParser(merge_short_paragraphs=False)
    markdown = """# CPO

## Charts

![](./Co_Packaged_Optics_(CPO)_images/img_098.png)
"""

    project = parser.parse(markdown)
    paragraph = project.sections[0].paragraphs[0]

    assert paragraph.element_type == ElementType.IMAGE
    assert paragraph.source == "./Co_Packaged_Optics_(CPO)_images/img_098.png"
    assert paragraph.source_html == (
        '<img src="./Co_Packaged_Optics_(CPO)_images/img_098.png" />'
    )
