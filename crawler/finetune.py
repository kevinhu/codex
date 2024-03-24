# %%
import copy
from dataclasses import dataclass
from typing import Any, Sequence, TypedDict

import bitsandbytes as bnb
import composer
import torch
import transformers
from composer import Trainer
from composer.algorithms import GradientClipping
from composer.loggers import WandBLogger
from composer.utils import dist
from coolname import generate_slug
from torch.utils.data import DataLoader
from composer import ComposerModel
from composer.core import Batch
from torch.utils.data import Dataset
import composer.optim
import torchmetrics
import torchmetrics.aggregation
import polars as pl


CHATML_TEMPLATE = "{% for message in messages %}{{'<|im_start|>' + message['role'] + '\n' + message['content'] + '<|im_end|>' + '\n'}}{% endfor %}{% if add_generation_prompt %}{{ '<|im_start|>assistant\n' }}{% endif %}"
IGNORE_INDEX = -100

WANDB_PROJECT = "paper_analyzer"
NUM_EPOCHS = 3
LR = 1e-6
BASE_MODEL = "mlabonne/NeuralHermes-2.5-Mistral-7B"
NUM_TEST = 64


class ValTop5Error(torchmetrics.aggregation.MeanMetric):
    def __init__(self):
        super().__init__()


class ValTop1Error(torchmetrics.aggregation.MeanMetric):
    def __init__(self):
        super().__init__()


class ValLoss(torchmetrics.aggregation.MeanMetric):
    def __init__(self):
        super().__init__()


def topk_error(logits: torch.Tensor, labels: torch.Tensor, k: int):
    shift_logits = logits[..., :-1, :].contiguous()
    shift_labels = labels[..., 1:].contiguous().to(torch.long)
    _, indices = torch.topk(shift_logits, k=k, dim=-1)
    correct = torch.sum(
        (indices == shift_labels.unsqueeze(-1)) & (shift_labels.unsqueeze(-1) != -100),
        dim=-1,
    )

    total_labels = torch.sum(shift_labels != -100)

    if total_labels == 0:
        return

    correct = torch.sum(correct > 0).item()

    return 1 - (correct / total_labels.item())


class ComposerCausalLM(ComposerModel):
    def __init__(self, model):
        super().__init__()
        f"cuda:{dist.get_global_rank()}"
        self.model = model

        self.val_top5_error = ValTop5Error()
        self.val_top1_error = ValTop1Error()
        self.val_loss = ValLoss()

    def forward(self, batch):
        return self.model(input_ids=batch["input_ids"], labels=batch["labels"])

    def eval_forward(
        self,
        batch,
        outputs: Any | None = None,
    ):
        return self.model(input_ids=batch["input_ids"], labels=batch["labels"])

    def update_metric(self, batch, outputs, metric):
        if isinstance(metric, ValTop5Error):
            metric.update(topk_error(outputs.logits, batch["labels"], 5))  # type: ignore
        if isinstance(metric, ValTop1Error):
            metric.update(topk_error(outputs.logits, batch["labels"], 1))  # type: ignore
        elif isinstance(metric, ValLoss):
            metric.update(outputs.loss.item())

    def get_metrics(self, is_train=False):
        return (
            {}
            if is_train
            else {
                "val_top5_error": self.val_top5_error,
                "val_top1_error": self.val_top1_error,
                "val_loss": self.val_loss,
            }
        )

    def loss(
        self, outputs: Any, batch: Batch, *args, **kwargs
    ) -> torch.Tensor | Sequence[torch.Tensor]:
        return outputs.loss


class Example(TypedDict):
    instruction: str
    response: str


class InstructDataset(Dataset):
    def __init__(
        self,
        instructions: list[str],
        responses: list[str],
    ):
        super().__init__()

        # Formatting prompts based on whether a system column is provided
        self.instructions: list[str] = instructions

        # Formatting targets
        self.responses: list[str] = responses

    def __len__(self):
        return len(self.instructions)

    def __getitem__(self, i):
        return Example(
            instruction=self.instructions[i],
            response=self.responses[i],
        )


@dataclass
class InstructCollator(object):
    """Collate examples for supervised fine-tuning."""

    tokenizer: transformers.PreTrainedTokenizer | transformers.PreTrainedTokenizerFast

    def __call__(self, instances: list[Example]) -> dict[str, torch.Tensor]:
        instructions_tokenized = [
            self.tokenizer(  # type: ignore
                self.tokenizer.apply_chat_template(  # type: ignore
                    [
                        {
                            "role": "user",
                            "content": instance["instruction"],
                        },
                    ],
                    tokenize=False,
                    add_generation_prompt=True,
                ),
                return_tensors="pt",
                truncation=True,
            )["input_ids"][0]
            for instance in instances
        ]

        instruction_lengths = [x.shape[0] for x in instructions_tokenized]

        labels = [
            self.tokenizer(  # type: ignore
                self.tokenizer.apply_chat_template(  # type: ignore
                    [
                        {
                            "role": "user",
                            "content": instance["instruction"],
                        },
                        {
                            "role": "assistant",
                            "content": instance["response"],
                        },
                    ],
                    tokenize=False,
                    add_generation_prompt=False,
                ),
                return_tensors="pt",
                truncation=True,
            )["input_ids"][0]
            for instance in instances
        ]

        input_ids = copy.deepcopy(labels)

        for label, input_length in zip(labels, instruction_lengths):
            label[:input_length] = IGNORE_INDEX

        assert self.tokenizer.eos_token_id is not None

        # right padding
        input_ids = torch.nn.utils.rnn.pad_sequence(
            input_ids, batch_first=True, padding_value=self.tokenizer.eos_token_id
        )
        labels = torch.nn.utils.rnn.pad_sequence(
            labels, batch_first=True, padding_value=IGNORE_INDEX
        )

        # pad to multiple of 64
        pad_length = 64 - (labels.shape[1] % 64)
        if pad_length == 64:
            pad_length = 0
        input_ids = torch.nn.functional.pad(
            input_ids, (0, pad_length), value=self.tokenizer.eos_token_id
        )
        labels = torch.nn.functional.pad(labels, (0, pad_length), value=IGNORE_INDEX)

        input_ids = input_ids[:, : self.tokenizer.model_max_length]
        labels = labels[:, : self.tokenizer.model_max_length]

        # # left padding
        # input_ids = torch.nn.utils.rnn.pad_sequence(
        #     [x.flip(0) for x in input_ids],
        #     batch_first=True,
        #     padding_value=self.tokenizer.pad_token_id,
        # ).flip(1)
        # labels = torch.nn.utils.rnn.pad_sequence(
        #     [x.flip(0) for x in labels], batch_first=True, padding_value=IGNORE_INDEX
        # ).flip(1)

        return dict(
            input_ids=input_ids,
            labels=labels,
            attention_mask=input_ids.ne(self.tokenizer.eos_token_id),
        )


# %%
if __name__ == "__main__":
    dataset = pl.read_parquet("data/processed/finetune_responses.parquet")

    test_df = dataset[:NUM_TEST]
    train_df = dataset[NUM_TEST:]

    test_set = InstructDataset(
        instructions=test_df["user_text"].to_list(),
        responses=test_df["response"].to_list(),
    )

    train_set = InstructDataset(
        instructions=train_df["user_text"].to_list(),
        responses=train_df["response"].to_list(),
    )

    run_name = generate_slug()

    clipping_type = "norm"
    clipping_threshold = 0.1

    extra_tokens = []

    device = f"cuda:{dist.get_global_rank()}"

    print("Setting up model")
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        BASE_MODEL, padding_side="right"
    )
    tokenizer.model_max_length = 8192
    tokenizer.pad_token_id = tokenizer.eos_token_id

    if not tokenizer.chat_template:
        print("Setting chat template")
        tokenizer.chat_template = CHATML_TEMPLATE
        extra_tokens += ["<|im_start|>", "<|im_end|>"]
        extra_tokens = list(set(extra_tokens))
        tokenizer.add_special_tokens({"additional_special_tokens": extra_tokens})  # type: ignore

    orig_model = transformers.AutoModelForCausalLM.from_pretrained(  # type: ignore
        BASE_MODEL,
        device_map=device,
        torch_dtype=torch.bfloat16,
        attn_implementation="flash_attention_2",
    ).eval()  # type: ignore
    orig_model.gradient_checkpointing_enable()

    if not tokenizer.mask_token_id:
        tokenizer.add_special_tokens({"mask_token": tokenizer.eos_token})
    if not tokenizer.cls_token_id:
        tokenizer.add_special_tokens({"cls_token": tokenizer.eos_token})
    if not tokenizer.sep_token_id:
        tokenizer.add_special_tokens({"sep_token": tokenizer.eos_token})

    orig_model.config.vocab_size += len(extra_tokens)
    orig_model.resize_token_embeddings(orig_model.config.vocab_size)

    model = ComposerCausalLM(model=orig_model)

    print("Setting up collators")
    train_collator = InstructCollator(
        tokenizer,
    )
    test_collator = InstructCollator(
        tokenizer,
    )
    logger = WandBLogger(project=WANDB_PROJECT, name=run_name)

    train_sampler = dist.get_sampler(train_set, shuffle=True, drop_last=True)
    test_sampler = dist.get_sampler(test_set, shuffle=True, drop_last=True)

    gc = GradientClipping(
        clipping_type=clipping_type, clipping_threshold=clipping_threshold
    )

    print("Setting up trainer")
    trainer = Trainer(
        model=model,
        train_dataloader=DataLoader(
            train_set,
            batch_size=8,
            collate_fn=train_collator,
            sampler=train_sampler,
            num_workers=8,
            prefetch_factor=2,
        ),
        eval_dataloader=DataLoader(
            test_set,
            batch_size=1,
            collate_fn=test_collator,
            sampler=test_sampler,
            num_workers=8,
            prefetch_factor=2,
        ),
        max_duration=NUM_EPOCHS,
        device="gpu",
        optimizers=bnb.optim.AdamW8bit(
            model.parameters(),
            lr=LR * dist.get_world_size(),
            betas=(0.9, 0.999),
            eps=1e-8,
            weight_decay=0.001,
        ),
        schedulers=composer.optim.CosineAnnealingWithWarmupScheduler(
            t_warmup="0.125dur"
        ),
        precision="amp_bf16",
        loggers=logger,
        eval_interval="0.1dur",
        algorithms=[gc],
        run_name=run_name,
        device_train_microbatch_size=1,
        python_log_level="debug",
    )

    print("Starting training")
    trainer.fit()

    if dist.get_global_rank() == 0:
        orig_model.push_to_hub(
            "khu/paper_analyzer",
            private=True,
            create_pr=True,
            safe_serialization=True,
        )
        tokenizer.push_to_hub(
            "khu/paper_analyzer",
            private=True,
            create_pr=True,
        )
