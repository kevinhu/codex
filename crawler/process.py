# %%
from os import PathLike
from pathlib import Path
from types import TracebackType
from typing import Annotated, Any, Generic, Iterator, Literal, Optional, Type, TypeVar
import click
import orjson
from loguru import logger
from pydantic import BaseModel, BeforeValidator, Discriminator, Field
import multiprocessing

from tqdm import tqdm

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


BaseModelT = TypeVar("BaseModelT", bound=BaseModel)


class NdjsonReader(Generic[BaseModelT]):
    def __init__(
        self,
        path: "PathLike[Any]",
        model: type[BaseModelT],
        validate: bool = False,
        strict: bool = True,
    ):
        self.path = Path(path)
        self.model = model
        self.validate = validate
        self.strict = strict

    def __enter__(self):
        self.file = self.path.open("r")
        return self

    def __exit__(
        self, exc_type: Type[Exception], exc_value: Exception, traceback: TracebackType
    ):
        self.file.close()

    def __iter__(
        self,
    ) -> Iterator[BaseModelT]:
        for line in self.file:
            try:
                if self.validate:
                    yield self.model.model_validate_json(line)
                else:
                    parsed = orjson.loads(line)
                    yield self.model.model_construct(**parsed)
            except Exception as e:
                if self.strict:
                    raise e
                else:
                    logger.error(f"Error parsing line: {line}")
                    logger.error(e)


class InlinedParagraph(BaseModel):
    section: str | None = None
    text: str


def inline(paper: Paper) -> list[InlinedParagraph]:
    inlined_texts: list[InlinedParagraph] = []

    # section_title = None

    for paragraph in paper.body_text:
        # Skip the proofs
        if paragraph.content_type in [
            "proof",
            "list",
            "picture",
            "item",
        ]:
            continue

        if paragraph.section and (
            paragraph.section.startswith("Appendix")
            or paragraph.section.startswith("Supplementary")
            or paragraph.section.startswith("Acknowledgements")
            or paragraph.section.startswith("References")
            or paragraph.section.startswith("Proof")
        ):
            continue

        if paragraph.text.startswith("Lemma") or paragraph.text.startswith("Theorem"):
            continue

        # Sort the spans by start position in reverse order
        spans = sorted(
            paragraph.cite_spans + paragraph.ref_spans,
            key=lambda s: s.end,
            reverse=True,
        )

        text = paragraph.text

        for span in spans:
            # Get the reference text based on the span type
            if span.ref_id in paper.ref_entries:
                # ref_text = paper.ref_entries[span.ref_id].latex
                ref = paper.ref_entries[span.ref_id]
                if ref.type == "formula":
                    ref_text = f"${ref.latex.strip()}$"
                elif ref.type == "figure":
                    ref_text = f"<figure> {ref.caption.strip()}"
                elif ref.type == "table":
                    ref_text = f"<table> {ref.caption.strip()}"
            elif span.ref_id in paper.bib_entries:
                ref_text = ""
            else:
                continue

            # Replace the span text with the reference text
            text = text[: span.start] + ref_text + text[span.end :]

        # Remove the formula placeholders
        # if paragraph.section and paragraph.section != section_title:
        # inlined_texts.append(f"# {paragraph.section}\n{text}")
        # section_title = paragraph.section
        # else:
        # inlined_texts.append(text)

        inline_paragraph = InlinedParagraph(section=paragraph.section, text=text)
        inlined_texts.append(inline_paragraph)

    return inlined_texts


class ProcessedPaper(BaseModel):
    paper_id: str
    metadata: Metadata
    discipline: str
    abstract: Abstract
    bib_entries: dict[str, BibEntry]
    inlined_texts: list[InlinedParagraph]


def process_path(path: Path):
    output_path = Path("data/processed/inlined_papers") / path.name

    with open(output_path, "w") as f_out:
        with NdjsonReader(path, Paper, validate=True) as f:
            for paper in f:
                try:
                    inlined_texts = inline(paper)
                except Exception as e:
                    logger.error(f"Error processing {paper.paper_id}")
                    logger.error(e)
                    continue
                processed_paper = ProcessedPaper(
                    paper_id=paper.paper_id,
                    metadata=paper.metadata,
                    discipline=paper.discipline,
                    abstract=paper.abstract,
                    bib_entries=paper.bib_entries,
                    inlined_texts=inlined_texts,
                )
                # yield processed_paper
                f_out.write(processed_paper.model_dump_json(exclude_none=True))
                f_out.write("\n")

    return output_path


@click.group()
def cli():
    pass


@cli.command()
def process():
    paths = list(Path("data/raw/unarXive_230324_open_subset").rglob("*.jsonl"))

    logger.info(f"Processing {len(paths)} files")
    with multiprocessing.Pool(multiprocessing.cpu_count()) as pool:
        for p in tqdm(pool.imap_unordered(process_path, paths)):
            logger.info(f"Wrote {p}")


@cli.command()
def merge():
    processed_paths = list(Path("data/processed/inlined_papers").rglob("*.jsonl"))
    with open("data/processed/inlined_papers.jsonl", "w") as f_out:
        for path in tqdm(processed_paths, desc="Merging"):
            with open(path, "r") as f:
                for line in f:
                    f_out.write(line)


@cli.command()
def filter():
    with NdjsonReader(
        Path("data/processed/inlined_papers.jsonl"), ProcessedPaper, validate=True
    ) as r, open("data/processed/cs_inlined_papers.jsonl", "w") as w:
        for paper in tqdm(r, desc="Filtering"):
            if paper.metadata.categories.startswith("cs."):
                w.write(paper.model_dump_json(exclude_none=True))
                w.write("\n")


if __name__ == "__main__":
    cli()
