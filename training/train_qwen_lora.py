"""Fine-tune Qwen for Text2STL with LoRA/QLoRA.

Example:
python training/train_qwen_lora.py ^
  --dataset training/out/text_to_cadquery_sft.jsonl ^
  --model-name Qwen/Qwen3-8B ^
  --output-dir training/out/qwen3-8b-text2stl-lora ^
  --max-samples 2000

Run this on a CUDA GPU machine. The output is a LoRA adapter, not a full
merged model.
"""

from __future__ import annotations

import argparse
import inspect
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a Qwen LoRA adapter for Text2STL CadQuery generation.")
    parser.add_argument("--dataset", type=Path, required=True, help="Chat-style SFT JSONL path.")
    parser.add_argument("--model-name", default="Qwen/Qwen3-8B", help="Base Hugging Face model.")
    parser.add_argument("--output-dir", type=Path, default=Path("training/out/qwen3-8b-text2stl-lora"))
    parser.add_argument("--max-seq-length", type=int, default=2048)
    parser.add_argument("--max-samples", type=int, default=None, help="Use a small subset for a smoke test.")
    parser.add_argument("--eval-ratio", type=float, default=0.01)
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument("--save-steps", type=int, default=250)
    parser.add_argument("--logging-steps", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-4bit", action="store_true", help="Disable QLoRA 4-bit loading.")
    return parser.parse_args()


def require_training_imports():
    try:
        import torch
        from datasets import load_dataset
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
            DataCollatorForLanguageModeling,
            Trainer,
            TrainingArguments,
        )
    except ImportError as exc:
        raise SystemExit(
            "Missing training dependencies. Install them on the GPU machine with:\n"
            "  pip install -r training/requirements-train.txt\n"
            f"Original error: {exc}"
        ) from exc

    return {
        "torch": torch,
        "load_dataset": load_dataset,
        "LoraConfig": LoraConfig,
        "get_peft_model": get_peft_model,
        "prepare_model_for_kbit_training": prepare_model_for_kbit_training,
        "AutoModelForCausalLM": AutoModelForCausalLM,
        "AutoTokenizer": AutoTokenizer,
        "BitsAndBytesConfig": BitsAndBytesConfig,
        "DataCollatorForLanguageModeling": DataCollatorForLanguageModeling,
        "Trainer": Trainer,
        "TrainingArguments": TrainingArguments,
    }


def render_messages(tokenizer, messages: list[dict]) -> str:
    if getattr(tokenizer, "chat_template", None):
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)

    rendered: list[str] = []
    for message in messages:
        role = message.get("role", "user")
        content = str(message.get("content", "")).strip()
        rendered.append(f"<|{role}|>\n{content}")
    return "\n".join(rendered).strip()


def tokenize_dataset(dataset, tokenizer, max_seq_length: int):
    def tokenize_batch(batch):
        texts = [render_messages(tokenizer, messages) for messages in batch["messages"]]
        tokenized = tokenizer(
            texts,
            truncation=True,
            max_length=max_seq_length,
            padding=False,
        )
        tokenized["labels"] = [ids.copy() for ids in tokenized["input_ids"]]
        return tokenized

    return dataset.map(
        tokenize_batch,
        batched=True,
        remove_columns=dataset.column_names,
        desc="Tokenizing",
    )


def make_training_arguments(training_arguments_cls, args: argparse.Namespace, has_eval: bool):
    kwargs = {
        "output_dir": str(args.output_dir),
        "per_device_train_batch_size": args.batch_size,
        "per_device_eval_batch_size": args.batch_size,
        "gradient_accumulation_steps": args.grad_accum,
        "learning_rate": args.learning_rate,
        "num_train_epochs": args.epochs,
        "logging_steps": args.logging_steps,
        "save_steps": args.save_steps,
        "save_total_limit": 2,
        "warmup_ratio": 0.03,
        "lr_scheduler_type": "cosine",
        "report_to": "none",
        "seed": args.seed,
        "gradient_checkpointing": True,
    }

    params = inspect.signature(training_arguments_cls.__init__).parameters
    if "optim" in params:
        kwargs["optim"] = "paged_adamw_8bit" if not args.no_4bit else "adamw_torch"
    if "eval_strategy" in params:
        kwargs["eval_strategy"] = "steps" if has_eval else "no"
    elif "evaluation_strategy" in params:
        kwargs["evaluation_strategy"] = "steps" if has_eval else "no"
    if has_eval:
        kwargs["eval_steps"] = args.save_steps

    return training_arguments_cls(**kwargs)


def main() -> None:
    args = parse_args()
    libs = require_training_imports()

    torch = libs["torch"]
    if not args.dataset.exists():
        raise SystemExit(f"Dataset not found: {args.dataset}")
    if not torch.cuda.is_available():
        raise SystemExit("CUDA GPU was not detected. Run this on the GPU PC.")

    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    tokenizer = libs["AutoTokenizer"].from_pretrained(args.model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    quantization_config = None
    if not args.no_4bit:
        quantization_config = libs["BitsAndBytesConfig"](
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=compute_dtype,
            bnb_4bit_use_double_quant=True,
        )

    model = libs["AutoModelForCausalLM"].from_pretrained(
        args.model_name,
        quantization_config=quantization_config,
        torch_dtype=compute_dtype,
        device_map="auto",
        trust_remote_code=True,
    )
    model.config.use_cache = False

    if not args.no_4bit:
        model = libs["prepare_model_for_kbit_training"](model)

    lora_config = libs["LoraConfig"](
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = libs["get_peft_model"](model, lora_config)
    model.print_trainable_parameters()

    dataset = libs["load_dataset"]("json", data_files=str(args.dataset), split="train")
    if args.max_samples is not None:
        dataset = dataset.select(range(min(args.max_samples, len(dataset))))

    if args.eval_ratio > 0 and len(dataset) > 1:
        split = dataset.train_test_split(test_size=args.eval_ratio, seed=args.seed)
        train_dataset = split["train"]
        eval_dataset = split["test"]
    else:
        train_dataset = dataset
        eval_dataset = None

    train_dataset = tokenize_dataset(train_dataset, tokenizer, args.max_seq_length)
    if eval_dataset is not None:
        eval_dataset = tokenize_dataset(eval_dataset, tokenizer, args.max_seq_length)

    training_args = make_training_arguments(libs["TrainingArguments"], args, eval_dataset is not None)
    data_collator = libs["DataCollatorForLanguageModeling"](tokenizer=tokenizer, mlm=False)
    trainer = libs["Trainer"](
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=data_collator,
    )

    trainer.train()
    trainer.save_model(str(args.output_dir))
    tokenizer.save_pretrained(str(args.output_dir))
    print(f"Saved LoRA adapter to {args.output_dir}")


if __name__ == "__main__":
    main()
