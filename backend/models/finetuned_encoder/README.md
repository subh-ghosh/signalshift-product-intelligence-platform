---
tags:
- sentence-transformers
- sentence-similarity
- feature-extraction
- generated_from_trainer
- dataset_size:57
- loss:TripletLoss
base_model: sentence-transformers/all-MiniLM-L6-v2
widget:
- source_sentence: Can't play the movie I want to continue watch. it keep saying connection
    issue but I can watch other movie.
  sentences:
  - Netflix now want u to pay an $7 every month for more than 1 person to watch it
    not even 2 ppl r allowed to watch it on different accounts i would recommend Hulu
    or any other movie streaming platforms instead
  - I want jazzcash or easy paisa option to pay plan because I doesn't have any credit
    card or debit card😑
  - not all episodes will play. Netflix says it's my phone not working but my phone
    works for 100% of other apps. I have to clear data and cache everytime I want
    to watch a new episode.
- source_sentence: While watching a movie, it gets stuck in the middle and doesn’t
    play no matter what I do. The streaming is really pathetic. Every time I pay ₹150,
    but still I get such a terrible service. I just wanted Netflix, but I’ve used
    at least 8–10 paid accounts and now I’ll stop them all because every app has problems.
    Such a useless application!
  sentences:
  - fix your video its stuck and never able to watch again i will cancel my membership
    forever
  - The ads are so annoying now. The whole point of streaming was no ads. If I wanted
    to watch ads, I would use cable. Unsubscribing.
  - I can't watch my movies again, and it is not my network, too It continues to load
    and will never come, and it will never
- source_sentence: I can't watch my movies again, and it is not my network, too It
    continues to load and will never come, and it will never
  sentences:
  - If I took subscription then I will be albe to see WWE live?Why I am unable to
    see survivor series? Shame of Netflix. My money got waste
  - Has a much better selection of movies & TV shows than the other pay to use streaming
    apps do. The monthly subscription price has also drastically decreased to a more
    affordable price which is why I signed up again for a new subscription to Netflix.
    I dropped them a couple years ago bc the monthly price was way too high for what
    you got. Now you get what you pay for & more.
  - Suddenly, I couldn't watch netflix while in a call on messenger unlike before
    I have no problem with it.
- source_sentence: Netflix took my payment !! whenever I try to watch something, it
    keeps saying my payment is pending. This is unacceptable, I’ve already paid, yet
    I can’t access anything. I'm never downloading it again. Refund my money as soon
    as possible !!
  sentences:
  - Experience seems to get worse over time... -Games constantly being pushed when
    I have no interest in playing games on a video streaming service. -My 'currently
    watching' list keeps vanishing, and when it doesn't I would prefer if it was always
    at the top and I didn't have to go searching for it -App claims I am using a VPN
    when I'm not, and the help page implies that VPNs are allowed for premium paying
    members, which I am, so why is it complaining to begin with?
  - Netflix is actively freezing during pivotal scenes in shows and movies essentially
    changing history through views
  - chor hai netflix wala after money is deducted from my account after sending email
    with with the payment screenshot they are denying that payment not received chor
    sala & when I spoke to the customer care they are saying payment has been received
    but it will be paid to you again after 30 day lost of people have faced the same
    problem i request everyone to boycott netflix
- source_sentence: r u kidding me? i am watching and suddenly everything is frozen
  sentences:
  - AM CANCELLING DUE TO YOUR EXTREMELY PETTY REGULATIONS BECAUSE AS A SINGLE PERSON,
    PAYING FOR 2 SCREENS, YOU LET ME WATCH WHAT I LIKE, BUT IF I TURN MY VPN ON TO
    ANOTHER COUNTRY, YOU BAN ME FROM WATCHING IT. BUT YOU KNOW FULL WELL, I'M IN NEW
    ZEALAND BUT YOU BAN ME ANYWAY.SO I HAVE TO TURN MY VPN OFF TO WATCH YOUR GARBAGE
    SO I'M CANCELING AND TAKING SERVICES ELSEWHERE. BECAUSE IT IS PETTY WHEN YOU THINK
    ABOUT IT, IT IS SO CHILDISH AND PETTY AND IMMATURE SCREW YOU NETFLIX.
  - Netflix is actively freezing during pivotal scenes in shows and movies essentially
    changing history through views
  - AM CANCELLING DUE TO YOUR EXTREMELY PETTY REGULATIONS BECAUSE AS A SINGLE PERSON,
    PAYING FOR 2 SCREENS, YOU LET ME WATCH WHAT I LIKE, BUT IF I TURN MY VPN ON TO
    ANOTHER COUNTRY, YOU BAN ME FROM WATCHING IT. BUT YOU KNOW FULL WELL, I'M IN NEW
    ZEALAND BUT YOU BAN ME ANYWAY.SO I HAVE TO TURN MY VPN OFF TO WATCH YOUR GARBAGE
    SO I'M CANCELING AND TAKING SERVICES ELSEWHERE. BECAUSE IT IS PETTY WHEN YOU THINK
    ABOUT IT, IT IS SO CHILDISH AND PETTY AND IMMATURE SCREW YOU NETFLIX.
pipeline_tag: sentence-similarity
library_name: sentence-transformers
metrics:
- cosine_accuracy
model-index:
- name: SentenceTransformer based on sentence-transformers/all-MiniLM-L6-v2
  results:
  - task:
      type: triplet
      name: Triplet
    dataset:
      name: val
      type: val
    metrics:
    - type: cosine_accuracy
      value: 0.5714285969734192
      name: Cosine Accuracy
---

# SentenceTransformer based on sentence-transformers/all-MiniLM-L6-v2

This is a [sentence-transformers](https://www.SBERT.net) model finetuned from [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2). It maps sentences & paragraphs to a 384-dimensional dense vector space and can be used for retrieval.

## Model Details

### Model Description
- **Model Type:** Sentence Transformer
- **Base model:** [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) <!-- at revision c9745ed1d9f207416be6d2e6f8de32d1f16199bf -->
- **Maximum Sequence Length:** 256 tokens
- **Output Dimensionality:** 384 dimensions
- **Similarity Function:** Cosine Similarity
- **Supported Modality:** Text
<!-- - **Training Dataset:** Unknown -->
<!-- - **Language:** Unknown -->
<!-- - **License:** Unknown -->

### Model Sources

- **Documentation:** [Sentence Transformers Documentation](https://sbert.net)
- **Repository:** [Sentence Transformers on GitHub](https://github.com/huggingface/sentence-transformers)
- **Hugging Face:** [Sentence Transformers on Hugging Face](https://huggingface.co/models?library=sentence-transformers)

### Full Model Architecture

```
SentenceTransformer(
  (0): Transformer({'transformer_task': 'feature-extraction', 'modality_config': {'text': {'method': 'forward', 'method_output_name': 'last_hidden_state'}}, 'module_output_name': 'token_embeddings', 'architecture': 'BertModel'})
  (1): Pooling({'embedding_dimension': 384, 'pooling_mode': 'mean', 'include_prompt': True})
  (2): Normalize({})
)
```

## Usage

### Direct Usage (Sentence Transformers)

First install the Sentence Transformers library:

```bash
pip install -U sentence-transformers
```
Then you can load this model and run inference.
```python
from sentence_transformers import SentenceTransformer

# Download from the 🤗 Hub
model = SentenceTransformer("sentence_transformers_model_id")
# Run inference
sentences = [
    'r u kidding me? i am watching and suddenly everything is frozen',
    'Netflix is actively freezing during pivotal scenes in shows and movies essentially changing history through views',
    "AM CANCELLING DUE TO YOUR EXTREMELY PETTY REGULATIONS BECAUSE AS A SINGLE PERSON, PAYING FOR 2 SCREENS, YOU LET ME WATCH WHAT I LIKE, BUT IF I TURN MY VPN ON TO ANOTHER COUNTRY, YOU BAN ME FROM WATCHING IT. BUT YOU KNOW FULL WELL, I'M IN NEW ZEALAND BUT YOU BAN ME ANYWAY.SO I HAVE TO TURN MY VPN OFF TO WATCH YOUR GARBAGE SO I'M CANCELING AND TAKING SERVICES ELSEWHERE. BECAUSE IT IS PETTY WHEN YOU THINK ABOUT IT, IT IS SO CHILDISH AND PETTY AND IMMATURE SCREW YOU NETFLIX.",
]
embeddings = model.encode(sentences)
print(embeddings.shape)
# [3, 384]

# Get the similarity scores for the embeddings
similarities = model.similarity(embeddings, embeddings)
print(similarities)
# tensor([[1.0000, 0.5066, 0.1820],
#         [0.5066, 1.0000, 0.3043],
#         [0.1820, 0.3043, 1.0000]])
```
<!--
### Direct Usage (Transformers)

<details><summary>Click to see the direct usage in Transformers</summary>

</details>
-->

<!--
### Downstream Usage (Sentence Transformers)

You can finetune this model on your own dataset.

<details><summary>Click to expand</summary>

</details>
-->

<!--
### Out-of-Scope Use

*List how the model may foreseeably be misused and address what users ought not to do with the model.*
-->

## Evaluation

### Metrics

#### Triplet

* Dataset: `val`
* Evaluated with [<code>TripletEvaluator</code>](https://sbert.net/docs/package_reference/sentence_transformer/evaluation.html#sentence_transformers.sentence_transformer.evaluation.TripletEvaluator)

| Metric              | Value      |
|:--------------------|:-----------|
| **cosine_accuracy** | **0.5714** |

<!--
## Bias, Risks and Limitations

*What are the known or foreseeable issues stemming from this model? You could also flag here known failure cases or weaknesses of the model.*
-->

<!--
### Recommendations

*What are recommendations with respect to the foreseeable issues? For example, filtering explicit content.*
-->

## Training Details

### Training Dataset

#### Unnamed Dataset

* Size: 57 training samples
* Columns: <code>sentence_0</code>, <code>sentence_1</code>, and <code>sentence_2</code>
* Approximate statistics based on the first 57 samples:
  |         | sentence_0                                                                         | sentence_1                                                                         | sentence_2                                                                          |
  |:--------|:-----------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------|:------------------------------------------------------------------------------------|
  | type    | string                                                                             | string                                                                             | string                                                                              |
  | details | <ul><li>min: 7 tokens</li><li>mean: 46.02 tokens</li><li>max: 126 tokens</li></ul> | <ul><li>min: 7 tokens</li><li>mean: 47.88 tokens</li><li>max: 121 tokens</li></ul> | <ul><li>min: 10 tokens</li><li>mean: 46.32 tokens</li><li>max: 126 tokens</li></ul> |
* Samples:
  | sentence_0                                                                                                                                                                                                            | sentence_1                                                                                                                     | sentence_2                                                                                                                                                                                                                              |
  |:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
  | <code>Terrible quality you would think, for paying the pReMiUm uLtrA hD plan to get premium quality?? nah what a joke. IM ON A GREAT, FAST, STABLE WIFI AND I AM GETTING 240-480P QUALITY VIDEO!!!! disgusting</code> | <code>not working only buffering some time how to get fixed this problem</code>                                                | <code>can't watch without money it is very bad</code>                                                                                                                                                                                   |
  | <code>fix your video its stuck and never able to watch again i will cancel my membership forever</code>                                                                                                               | <code>some shows literally just don't play. its not a connection problem</code>                                                | <code>can't watch without money it is very bad</code>                                                                                                                                                                                   |
  | <code>It always says Too many devices watching</code>                                                                                                                                                                 | <code>Netflix is actively freezing during pivotal scenes in shows and movies essentially changing history through views</code> | <code>I'm a new subscriber and I've not been able to sign in. I paid for a month and I was debuted but Netflix has refused to let me use the account I paid for. This is now turning into a big scam. I regret wasting my money.</code> |
* Loss: [<code>TripletLoss</code>](https://sbert.net/docs/package_reference/sentence_transformer/losses.html#tripletloss) with these parameters:
  ```json
  {
      "distance_metric": "TripletDistanceMetric.EUCLIDEAN",
      "triplet_margin": 5
  }
  ```

### Training Hyperparameters
#### Non-Default Hyperparameters

- `per_device_train_batch_size`: 32
- `per_device_eval_batch_size`: 32
- `multi_dataset_batch_sampler`: round_robin

#### All Hyperparameters
<details><summary>Click to expand</summary>

- `per_device_train_batch_size`: 32
- `num_train_epochs`: 3
- `max_steps`: -1
- `learning_rate`: 5e-05
- `lr_scheduler_type`: linear
- `lr_scheduler_kwargs`: None
- `warmup_steps`: 0
- `optim`: adamw_torch_fused
- `optim_args`: None
- `weight_decay`: 0.0
- `adam_beta1`: 0.9
- `adam_beta2`: 0.999
- `adam_epsilon`: 1e-08
- `optim_target_modules`: None
- `gradient_accumulation_steps`: 1
- `average_tokens_across_devices`: True
- `max_grad_norm`: 1
- `label_smoothing_factor`: 0.0
- `bf16`: False
- `fp16`: False
- `bf16_full_eval`: False
- `fp16_full_eval`: False
- `tf32`: None
- `gradient_checkpointing`: False
- `gradient_checkpointing_kwargs`: None
- `torch_compile`: False
- `torch_compile_backend`: None
- `torch_compile_mode`: None
- `use_liger_kernel`: False
- `liger_kernel_config`: None
- `use_cache`: False
- `neftune_noise_alpha`: None
- `torch_empty_cache_steps`: None
- `auto_find_batch_size`: False
- `log_on_each_node`: True
- `logging_nan_inf_filter`: True
- `include_num_input_tokens_seen`: no
- `log_level`: passive
- `log_level_replica`: warning
- `disable_tqdm`: False
- `project`: huggingface
- `trackio_space_id`: trackio
- `eval_strategy`: no
- `per_device_eval_batch_size`: 32
- `prediction_loss_only`: True
- `eval_on_start`: False
- `eval_do_concat_batches`: True
- `eval_use_gather_object`: False
- `eval_accumulation_steps`: None
- `include_for_metrics`: []
- `batch_eval_metrics`: False
- `save_only_model`: False
- `save_on_each_node`: False
- `enable_jit_checkpoint`: False
- `push_to_hub`: False
- `hub_private_repo`: None
- `hub_model_id`: None
- `hub_strategy`: every_save
- `hub_always_push`: False
- `hub_revision`: None
- `load_best_model_at_end`: False
- `ignore_data_skip`: False
- `restore_callback_states_from_checkpoint`: False
- `full_determinism`: False
- `seed`: 42
- `data_seed`: None
- `use_cpu`: False
- `accelerator_config`: {'split_batches': False, 'dispatch_batches': None, 'even_batches': True, 'use_seedable_sampler': True, 'non_blocking': False, 'gradient_accumulation_kwargs': None}
- `parallelism_config`: None
- `dataloader_drop_last`: False
- `dataloader_num_workers`: 0
- `dataloader_pin_memory`: True
- `dataloader_persistent_workers`: False
- `dataloader_prefetch_factor`: None
- `remove_unused_columns`: True
- `label_names`: None
- `train_sampling_strategy`: random
- `length_column_name`: length
- `ddp_find_unused_parameters`: None
- `ddp_bucket_cap_mb`: None
- `ddp_broadcast_buffers`: False
- `ddp_backend`: None
- `ddp_timeout`: 1800
- `fsdp`: []
- `fsdp_config`: {'min_num_params': 0, 'xla': False, 'xla_fsdp_v2': False, 'xla_fsdp_grad_ckpt': False}
- `deepspeed`: None
- `debug`: []
- `skip_memory_metrics`: True
- `do_predict`: False
- `resume_from_checkpoint`: None
- `warmup_ratio`: None
- `local_rank`: -1
- `prompts`: None
- `batch_sampler`: batch_sampler
- `multi_dataset_batch_sampler`: round_robin
- `router_mapping`: {}
- `learning_rate_mapping`: {}

</details>

### Training Logs
| Epoch | Step | val_cosine_accuracy |
|:-----:|:----:|:-------------------:|
| 1.0   | 2    | 0.5714              |
| 2.0   | 4    | 0.5714              |
| 3.0   | 6    | 0.5714              |


### Training Time
- **Training**: 58.9 seconds

### Framework Versions
- Python: 3.13.7
- Sentence Transformers: 5.4.0
- Transformers: 5.5.3
- PyTorch: 2.11.0+cu130
- Accelerate: 1.13.0
- Datasets: 4.8.4
- Tokenizers: 0.22.2

## Citation

### BibTeX

#### Sentence Transformers
```bibtex
@inproceedings{reimers-2019-sentence-bert,
    title = "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks",
    author = "Reimers, Nils and Gurevych, Iryna",
    booktitle = "Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing",
    month = "11",
    year = "2019",
    publisher = "Association for Computational Linguistics",
    url = "https://arxiv.org/abs/1908.10084",
}
```

#### TripletLoss
```bibtex
@misc{hermans2017defense,
    title={In Defense of the Triplet Loss for Person Re-Identification},
    author={Alexander Hermans and Lucas Beyer and Bastian Leibe},
    year={2017},
    eprint={1703.07737},
    archivePrefix={arXiv},
    primaryClass={cs.CV}
}
```

<!--
## Glossary

*Clearly define terms in order to be accessible across audiences.*
-->

<!--
## Model Card Authors

*Lists the people who create the model card, providing recognition and accountability for the detailed work that goes into its construction.*
-->

<!--
## Model Card Contact

*Provides a way for people who have updates to the Model Card, suggestions, or questions, to contact the Model Card authors.*
-->