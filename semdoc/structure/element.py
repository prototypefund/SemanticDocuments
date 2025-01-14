from collections import defaultdict
from dataclasses import dataclass
from typing import Self
from enum import StrEnum, auto
from semdoc import logging
from .region import Region

logger = logging.getLogger("semdoc.element")


class ElementType(StrEnum):
    """The category of the Element."""

    Document = auto()  # the whole document
    Page = auto()  # a physical page
    Heading1 = auto()  # a first level heading
    Heading2 = auto()  # a second level heading
    Heading3 = auto()  # a third level heading
    Heading4 = auto()  # a fourth level heading
    Heading5 = auto()  # a fourth level heading
    Heading6 = auto()  # a fourth level heading
    Paragraph = auto()  # a logical paragraph of text
    TextArea = auto()  # a physical box containing text
    TableArea = auto()  # a physical box containig the depiction of a table
    Partition = auto()  # a physical area of some significance
    TextLine = auto()  # a physical area containing a continuous line of text
    Table = auto()  # a logical table
    TableRow = auto()
    TableCell = auto()
    PageHeader = auto()
    PageFooter = auto()
    Figure = auto()

    @property
    def is_block(self):
        return str(self) in [
            "heading1",
            "heading2",
            "heading3",
            "heading4",
            "heading5",
            "heading6",
            "paragraph",
            "tablecell",
            "table",
            "pageheader",
            "pagefooter",
        ]

    @property
    def is_heading(self):
        return str(self) in [
            "heading1",
            "heading2",
            "heading3",
            "heading4",
            "heading5",
            "heading6",
        ]


def is_logical(element):
    logical_categories = [
        ElementType.Document,
        ElementType.Heading1,
        ElementType.Heading2,
        ElementType.Heading3,
        ElementType.Heading4,
        ElementType.Paragraph,
        ElementType.Table,
        ElementType.TableRow,
        ElementType.TableCell,
        ElementType.TextLine,
    ]
    return element.category in logical_categories


def geometric_sorter(element):
    region = element.region()
    if not region:
        return (0, 0)
    page = region.page_no
    x, y = region.x, region.y
    return (page, x + y * 5)


def table_sorter(element):
    region = element.region()
    page = region.page_no
    x, y = region.x, region.y
    return (page, y, x)


# class Element:
#     def __init__(self, type: ElementType):
#         self.type = type
#         self.children = []

#     def add_child(self, child):
#         self.children.append(child)

#     def iter_children(self, predicate=lambda x: True, depth_first=True):
#         for c in self.children:
#             if predicate(c):
#                 yield c
#                 yield from c.iter_predicate(predicate, depth_first)

#     def get_text(self):
#         return ""


class Element:
    """A node in the tree representation of documents.

    Elements can denote physical, organizational or logical propositions about
    (parts of) a document. An Element is characterized by three properties:
    - The category of the element, see ElementType
    - A region in the physical document it refers to.
    - A number of properties it asserts about this region.
    """

    def __init__(self, category: ElementType):
        self.children = list()
        self.category = category
        self.properties = defaultdict(list)
        self.parent = None

    def __repr__(self):
        return f"Element({self.category!r}, children={self.children!r}, properties={self.properties!r})"

    def iter_regions(self):
        if "region" in self.properties:
            region = self.get_property("region")
            yield region
        else:
            yield from []

    def set_property(self, key: str, value, source: str, confidence: float = 1.0):
        """TODO: This should go into the Property object"""
        prop = Property(key, value, source, confidence)
        self.properties[key].append(prop)

    def get(self, key: str):
        try:
            value = self.get_property(key)
        except KeyError:
            return None
        return value

    def get_property(self, key: str):
        """TODO This should go into the Property object"""
        if key not in self.properties:
            raise KeyError()
        data = self.properties[key]
        max_conf = -1
        strongest = None
        for prop in data:
            if prop.confidence > max_conf:
                strongest = prop
        if strongest:
            return strongest.value
        else:
            raise KeyError()

    def set_text(self, text: str, source: str, confidence: float = 1.0):
        prop = Property("text", text, source, confidence)
        self.properties["text"].append(prop)

    def add(self, element: Self):
        self._add(element)

    def _add(self, element: Self):
        self.children.append(element)
        element.parent = self

    def remove(self, element: Self):
        try:
            self.children.remove(element)
        except ValueError:
            logger.warn("tried to remove element that was not a child")
        else:
            element.parent = None

    def __len__(self):
        return len(self.children)

    def __getitem__(self, index):
        return self.children[index]

    def get_text(self):
        if "text" in self.properties:
            return self.get_property("text")
        else:
            return ""

    def region(self) -> Region:
        if "region" in self.properties:
            return self.get("region")

    def children_ordered(self):
        yield from sorted(self.children, key=lambda c: c.y and c.y)

    def to_dict(self):
        children = [child.to_dict() for child in self.children]
        properties = {key: self.get_property(key) for key in self.properties.keys()}
        return {
            "category": self.category,
            "children": children,
            "properties": properties,
        }

    def iter_children(self, filter=None, depth_first=True):
        for child in sorted(self.children, key=geometric_sorter):
            if (not filter) or filter(child):
                yield child
            yield from child.iter_children(filter, depth_first)


@dataclass
class Property:
    def __init__(self, key: str, value, source: str, confidence: float):
        if not 0 <= confidence <= 1:
            raise ValueError(f"Invalid confidence: {confidence}")
        self.key = key
        self.value = value
        self.confidence = confidence
        self.source = source

    def __repr__(self):
        return f"Property({self.key!r}, {self.value!r}, {self.source!r}, {self.confidence!r})"

    def __str__(self):
        return f"{self.key}: {self.value} ({self.source}: {self.confidence})"


def is_page(e: Element):
    category = e.category
    return category == ElementType.Page
