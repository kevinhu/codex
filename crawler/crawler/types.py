# %%
from typing import Annotated, Literal, Optional, TypeVar
from pydantic import BaseModel, BeforeValidator, Discriminator, Field


T = TypeVar("T")


def falsy_to_none(x: T) -> T | None:
    """
    Sets falsy values to None. We'd like None values to not be included
    in the model dumps to save tokens in prompts.
    """
    return x or None


FalsyToNone = Annotated[T | None, BeforeValidator(falsy_to_none)]


class Version(BaseModel):
    version: str
    created: str


class Span(BaseModel):
    start: int
    end: int
    text: str
    ref_id: str


class Paragraph(BaseModel):
    section: str | None
    sec_number: str
    sec_type: str
    # content_type: Literal[
    #     "paragraph",
    #     "proof",
    #     "list",
    #     "picture",
    #     "item",
    #     "label",
    #     "line",
    #     "theindex",
    #     "hi",
    #     "alt_head",
    #     "listing",
    #     "pic-put",
    #     "marginpar",
    #     "headings",
    #     "cleardoublepage",
    #     "References",
    #     "minipage",
    #     "Metadata",
    #     "epigraph",
    #     "fixfoot",
    #     "reference",
    #     "epitext",
    #     "FiXme",
    #     "References.",
    #     "REFERENCES",
    #     "abstract",
    #     "pic-frame",
    #     "mbox",
    #     "anchor",
    #     "Ovalbox",
    #     "R",
    #     "listoftables",
    #     "listoffigures",
    #     "hfill",
    #     "vfilneg",
    #     "samepage",
    #     "Reference",
    #     "maketitle",
    #     "xref",
    #     "TeX",
    #     "LaTeX",
    #     "pic-multiput",
    # ]
    content_type: str
    text: str
    cite_spans: list[Span]
    ref_spans: list[Span]


class ArticleId(BaseModel):
    open_alex_id: FalsyToNone[str] = None
    arxiv_id: FalsyToNone[str] = None
    pubmed_id: FalsyToNone[str] = None
    pmc_id: FalsyToNone[str] = None
    doi: FalsyToNone[str] = None
    arxiv_id: FalsyToNone[str] = None


class EmbeddedArxiv(BaseModel):
    id: str
    text: str | None = None
    start: int | None = None
    end: int | None = None


class EmbeddedLink(BaseModel):
    url: str
    text: str | None = None
    start: int | None = None
    end: int | None = None


class BibEntry(BaseModel):
    bib_entry_raw: str
    contained_arXiv_ids: list[EmbeddedArxiv]
    contained_links: list[EmbeddedLink]
    discipline: str | None = None
    ids: ArticleId | None = None


class LatexRefEntry(BaseModel):
    latex: str
    type: Literal["formula"]


class FigureRefEntry(BaseModel):
    caption: str
    type: Literal["figure"]


class TableRefEntry(BaseModel):
    caption: str
    type: Literal["table"]


class Metadata(BaseModel):
    id: str
    submitter: str | None = None
    authors: str
    title: str
    # comments: str
    journal_ref: Optional[str] = Field(None, alias="journal-ref")
    doi: Optional[str] = Field(None, alias="doi")
    report_no: Optional[str] = Field(None, alias="report-no")
    categories: str
    license: str
    abstract: str
    versions: list[Version]
    update_date: str
    authors_parsed: list[list[FalsyToNone[str]]]


class Abstract(BaseModel):
    section: str
    text: str
    cite_spans: list[Span]
    ref_spans: list[Span]


class Paper(BaseModel):
    paper_id: str
    _pdf_hash: Optional[str]
    _source_hash: str
    _source_name: str
    metadata: Metadata
    discipline: str
    abstract: Abstract
    body_text: list[Paragraph]
    bib_entries: dict[str, BibEntry]
    ref_entries: dict[
        str,
        Annotated[
            LatexRefEntry | FigureRefEntry | TableRefEntry, Discriminator("type")
        ],
    ]


class InlinedParagraph(BaseModel):
    section: str | None = None
    text: str


class ProcessedPaper(BaseModel):
    paper_id: str
    metadata: Metadata
    discipline: str
    abstract: Abstract
    bib_entries: dict[str, BibEntry]
    inlined_texts: list[InlinedParagraph]
