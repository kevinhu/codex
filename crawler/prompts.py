# %%
from crawler.types import ProcessedPaper
from pydantic import BaseModel


class PaperAnalysisPrompt(BaseModel):
    paper: ProcessedPaper

    def compile_prompt(self):
        system_text = """\
Your task is to index machine learning research papers for a knowledge base. You are provided with Markdown text of a research paper.
Read the following instructions and return your response as a JSON object of type `Response` inside a Markdown code block. Keep your JSON concise by omitting missing properties instead of explicitly setting them to `null`, `undefined`, or an empty string/array. Do not indent your JSON response.

```ts
type Response = {
    // Extract all findings, results, and insights from the paper. Required.
    findings: Finding[];
    // List all topics mentioned in the paper. Required.
    tasks: Task[];
    // List all benchmarks mentioned in the paper. Required.
    benchmarks: Benchmark[];
    // List all models mentioned in the paper. Required.
    models: Model[];
    // List all methods mentioned in the paper. Required.
    methods: Method[];
    // List all datasets mentioned in the paper. Required.
    datasets: Dataset[];
};

// List all informative findings from the paper because the original will be discarded later. Required.
type Finding = {
    // Describe the finding in a brief paragraph. Use at most five sentences.
    description: string;
    
    // Short name for the finding that could be used to retrieve it in a search engine.
    name: string;
    
    // Unique identifier for the Finding. Use only lowercase alphanumeric characters and underscores. Required.
    slug: string;
};

type Topic = {
    // Describe the topic in a brief paragraph. Use at most five sentences.
    description: string;

    // Short name for the topic that could be used to retrieve it in a search engine.
    name: string;

    // Unique identifier for the Topic. Use only lowercase alphanumeric characters and underscores. Required.
    slug: string;

    // If this paper is the first to introduce the topic, set this to true. Otherwise, set it to false. Required.
    primary: boolean;
    
    // Findings that mention the topic. Reference these by their slugs. Must not be empty.
    findings: string[];
}

// A task is a specific problem class. For example, "sentiment analysis" is a task. Other tasks may include "named entity recognition" or "GPU utilization".
type Task = Topic & {
    type: "task";
};

// A benchmark is a standardized evaluation that evaluates the performance of a model on a specific task. For example, "GLUE" is a benchmark. Do not create metrics as benchmarks; include those in the benchmark description instead.
type Benchmark = Topic & {
    type: "benchmark";
};

// Specific models listed in the dataset. For example, "BERT" is a specific model of the "transformer" method.
type Model = Topic & {
    type: "model";
};

// A method is a technique or algorithm used to solve a specific task. For example, a "convolutional neural network" is a type of method.
type Method = Topic & {
    type: "method";
};

// A dataset is a collection of data used to train or evaluate a model. For example, "MNIST" is a dataset.
type Dataset = Topic & {
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
"""

        return system_text + "\n" + user_text


with open("data/raw/test.json", "r") as f:
    paper = ProcessedPaper.model_validate_json(f.read())

    prompt = PaperAnalysisPrompt(paper=paper)

    print(prompt.compile_prompt())
