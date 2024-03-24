# %%
import re
from typing import Annotated, Literal, Optional, Self, TypeVar
from uuid import uuid4
from pydantic import (
    BaseModel,
    BeforeValidator,
    Discriminator,
    Field,
    StringConstraints,
    model_validator,
)


T = TypeVar("T")


MAX_PAPER_LENGTH = 16_000


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


class PaperAnalysisPrompt(BaseModel):
    paper: ProcessedPaper

    def compile_prompt(self):
        system_text = """\
Your task is to index machine learning research papers for a knowledge base. Given Markdown text of a research paper, your goal is to extract all relevant information and return it in a structured format.

Read the following instructions and return your response as a JSON object of type `Response` inside a Markdown code block.

```ts
type Response = {
    // Extract all findings, results, and insights from the paper. Remember, assume a relatively basic level of background knowledge, so be thorough in picking up information. Required.
    findings: Finding[];
    // List all tasks discussed in the paper. Required.
    tasks: Task[];
    // List all benchmarks discussed in the paper. Required.
    benchmarks: Benchmark[];
    // List all architectures discussed in the paper. Required.
    architectures: Architecture[];
    // List all models discussed in the paper. Required.
    models: Model[];
    // List all methods discussed in the paper. Required.
    methods: Method[];
    // List all datasets discussed in the paper. Required.
    datasets: Dataset[];
};

// List all informative findings from the paper because the original will be discarded later. Required.
// Every finding must be named to at least one topic later. Make sure you mention these topics by name so the connections are apparent.
type Finding = {
    // Unique identifier for the Finding. Use only lowercase alphanumeric characters and underscores. Required.
    slug: string;
    // Short name for the finding that could be used to retrieve it in a search engine. Required.
    name: string;
    // A clear, accessible, and impartial summary of the finding. Use at most five sentences. The description should make sense when read alone. Required.
    description: string;
};

// A topic is a concept or idea that is discussed in the paper and linked to findings. Do not merge similar topics into one.
type BaseTopic = {
    // Unique identifier for the Topic. Use only lowercase alphanumeric characters and underscores. Required.
    slug: string;
    // Short name for the topic that could be used to retrieve it in a search engine. Required.
    name: string;
    // A clear, accessible, and impartial summary of the topic. Use at most five sentences. The description should make sense when read out of context. Required.
    description: string;
    // Findings related to the topic. Reference these by their slugs. Must not be empty. Required.
    linked_findings: string[];
};

// A task is a specific problem class. For example, "sentiment analysis" is a task. Other tasks may include "named entity recognition" or "GPU utilization". Do not merge similar tasks into one.
// Each task must be linked to at least one finding.
type Task = BaseTopic & {
    type: "task";
};

// A benchmark is a standardized evaluation suite that evaluates the performance of a model on a specific task. Only create benchmarks if the name and description are clear. Do not count metrics such as BLEU as benchmarks. Do not merge similar benchmarks into one.
// Each benchmark must be linked to at least one finding.
type Benchmark = BaseTopic & {
    type: "benchmark";
};

// An architecture is a specific type of model. For example, "LSTM" is an architecture. Do not merge similar architectures into one.
// Each architecture must be linked to at least one finding.
type Architecture = BaseTopic & {
    type: "architecture";
};

// A specific instance of a model listed in the paper. For example, "BERT" is a model. General architectures like "transformer" should not be listed as models. Do not merge similar models into one.
// Each model must be linked to at least one finding.
type Model = BaseTopic & {
    type: "model";
};

// A method is a technique or algorithm. Metrics should be counted as Methods instead of Benchmarks. For example, a "convolutional neural network" is a type of method. Do not merge similar methods into one.
// Each method must be linked to at least one finding.
type Method = BaseTopic & {
    type: "method";
};

// A dataset is a collection of data used to train or evaluate a model. For example, "MNIST" is a dataset.
// Each dataset must be linked to at least one finding. Only create datasets if the name and description are clear. Do not merge similar datasets into one.
type Dataset = BaseTopic & {
    type: "dataset";
};
```
"""

        return system_text + self.user_text

    @property
    def user_text(self):
        paper_text = ""

        current_section = None

        for paragraph in self.paper.inlined_texts:
            # paper_text += paragraph.text + "\n"
            if paragraph.section and paragraph.section.strip() != current_section:
                paper_text += f"## {paragraph.section.strip()}\n"
                current_section = paragraph.section.strip()

            paper_text += paragraph.text.strip() + "\n"

        user_text = f"""\
```markdown
# {self.paper.metadata.title.strip()}

## Abstract
{self.paper.abstract.text.strip()}

{paper_text[:MAX_PAPER_LENGTH]}
```

When extracting information, assume a relatively basic level of background knowledge. Your response should be concise and informative, focusing on the key aspects of the paper. Keep your JSON concise by omitting missing properties instead of explicitly setting them to `null`, `undefined`, or an empty string/array. Do not indent your JSON response.
"""
        return user_text


SlugStr = Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]+$")]


class Finding(BaseModel):
    slug: SlugStr
    name: str
    description: str


class Topic(BaseModel):
    slug: SlugStr
    name: str
    description: str
    linked_findings: set[SlugStr]


class Task(Topic):
    type: str = "task"


class Benchmark(Topic):
    type: str = "benchmark"


class Architecture(Topic):
    type: str = "architecture"


class Model(Topic):
    type: str = "model"


class Method(Topic):
    type: str = "method"


class Dataset(Topic):
    type: str = "dataset"


class PaperAnalysisResponse(BaseModel):
    findings: list[Finding]

    tasks: list[Task]
    benchmarks: list[Benchmark]
    architectures: list[Architecture]
    models: list[Model]
    methods: list[Method]
    datasets: list[Dataset]

    @classmethod
    def from_response(cls, text: str) -> Self:
        parsed_text: str

        match = re.search(r"```[^\n]*\n(.*?)```", text, flags=re.DOTALL)
        if match:
            parsed_text = match.group(1).strip()
        else:
            parsed_text = text.strip()

        structured = cls.model_validate_json(parsed_text)
        return structured

    def to_response(self) -> str:
        return self.model_dump_json(exclude_none=True, by_alias=False)

    @model_validator(mode="after")
    def validate_response(self):
        finding_slugs = {finding.slug for finding in self.findings}

        assert len(finding_slugs) == len(self.findings), "Finding slugs must be unique."

        for task in self.tasks:
            assert task.linked_findings.issubset(
                finding_slugs
            ), "Task linked findings must be a subset of the findings."
        for benchmark in self.benchmarks:
            assert benchmark.linked_findings.issubset(
                finding_slugs
            ), "Benchmark linked findings must be a subset of the findings."
        for architecture in self.architectures:
            assert architecture.linked_findings.issubset(
                finding_slugs
            ), "Architecture linked findings must be a subset of the findings."
        for model in self.models:
            assert model.linked_findings.issubset(
                finding_slugs
            ), "Model linked findings must be a subset of the findings."
        for method in self.methods:
            assert method.linked_findings.issubset(
                finding_slugs
            ), "Method linked findings must be a subset of the findings."
        for dataset in self.datasets:
            assert dataset.linked_findings.issubset(
                finding_slugs
            ), "Dataset linked findings must be a subset of the findings."

        return self

    def all_topics(self):
        return (
            self.tasks
            + self.benchmarks
            + self.architectures
            + self.models
            + self.methods
            + self.datasets
        )


class ProcessedFinding(BaseModel):
    slug: str
    name: str
    description: str
    finding_id: str


class ProcessedTopic(BaseModel):
    slug: str
    name: str
    description: str
    type: Literal["task", "benchmark", "architecture", "model", "method", "dataset"]
    linked_finding_ids: list[str]
    topic_id: str


def process_response(response: PaperAnalysisResponse):
    processed_findings: list[ProcessedFinding] = []
    for finding in response.findings:
        processed_findings.append(
            ProcessedFinding(
                slug=finding.slug,
                name=finding.name,
                description=finding.description,
                finding_id=f"finding:{uuid4()}",
            )
        )

    finding_slug_to_id = {
        finding.slug: finding.finding_id for finding in processed_findings
    }

    processed_topics: list[ProcessedTopic] = []

    for task in response.tasks:
        processed_topics.append(
            ProcessedTopic(
                slug=task.slug,
                name=task.name,
                description=task.description,
                linked_finding_ids=[
                    finding_slug_to_id[slug] for slug in task.linked_findings
                ],
                topic_id=f"topic:{uuid4()}",
                type="task",
            )
        )
    for benchmark in response.benchmarks:
        processed_topics.append(
            ProcessedTopic(
                slug=benchmark.slug,
                name=benchmark.name,
                description=benchmark.description,
                linked_finding_ids=[
                    finding_slug_to_id[finding.slug]
                    for finding in response.findings
                    if finding.slug in benchmark.linked_findings
                ],
                topic_id=f"topic:{uuid4()}",
                type="benchmark",
            )
        )
    for architecture in response.architectures:
        processed_topics.append(
            ProcessedTopic(
                slug=architecture.slug,
                name=architecture.name,
                description=architecture.description,
                linked_finding_ids=[
                    finding_slug_to_id[finding.slug]
                    for finding in response.findings
                    if finding.slug in architecture.linked_findings
                ],
                topic_id=f"topic:{uuid4()}",
                type="architecture",
            )
        )
    for model in response.models:
        processed_topics.append(
            ProcessedTopic(
                slug=model.slug,
                name=model.name,
                description=model.description,
                linked_finding_ids=[
                    finding_slug_to_id[finding.slug]
                    for finding in response.findings
                    if finding.slug in model.linked_findings
                ],
                topic_id=f"topic:{uuid4()}",
                type="model",
            )
        )
    for method in response.methods:
        processed_topics.append(
            ProcessedTopic(
                slug=method.slug,
                name=method.name,
                description=method.description,
                linked_finding_ids=[
                    finding_slug_to_id[finding.slug]
                    for finding in response.findings
                    if finding.slug in method.linked_findings
                ],
                topic_id=f"topic:{uuid4()}",
                type="method",
            )
        )
    for dataset in response.datasets:
        processed_topics.append(
            ProcessedTopic(
                slug=dataset.slug,
                name=dataset.name,
                description=dataset.description,
                linked_finding_ids=[
                    finding_slug_to_id[finding.slug]
                    for finding in response.findings
                    if finding.slug in dataset.linked_findings
                ],
                topic_id=f"topic:{uuid4()}",
                type="dataset",
            )
        )

    return processed_findings, processed_topics


class PaperAnalysisRun(BaseModel):
    prompt: PaperAnalysisPrompt
    response: PaperAnalysisResponse
