# %%
from pathlib import Path
import click
from crawler.serializers import NdjsonReader
from loguru import logger
import multiprocessing
from crawler.types import Paper, InlinedParagraph, ProcessedPaper

from tqdm import tqdm


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
