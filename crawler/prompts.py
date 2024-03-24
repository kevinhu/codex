# %%
from crawler.types import ProcessedPaper
from pydantic import BaseModel


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
    body: string;
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

{paper_text}
```

When extracting information, assume a relatively basic level of background knowledge. Your response should be concise and informative, focusing on the key aspects of the paper. Keep your JSON concise by omitting missing properties instead of explicitly setting them to `null`, `undefined`, or an empty string/array. Do not indent your JSON response.
"""

        return system_text + "\n" + user_text


with open("data/raw/test.json", "r") as f:
    paper = ProcessedPaper.model_validate_json(f.read())

    prompt = PaperAnalysisPrompt(paper=paper)

    print(prompt.compile_prompt())
