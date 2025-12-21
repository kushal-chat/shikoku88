from datasets import load_dataset, DatasetDict, concatenate_datasets

# 1. Load Shikoku88 dataset from Hugging Face hub
dataset = load_dataset("kushalc1/goshuin-toukou")

# 3. Load Saigoku33 dataset from local folder
bendo = load_dataset("/Users/kushalchattopadhyay/Downloads/仕事/goshuin/goshuin/train")

# 4. saigoku33_ds is a DatasetDict, pick the train split
bendo = bendo['train']

# 5. Create DatasetDict with named splits
final_splits = DatasetDict({
    **dataset,
    "bando33": bendo,
})

print(final_splits)

# 6. Push to Hugging Face Hub
final_splits.push_to_hub("kushalc1/Goshuin-SFT")


# # Optional: sharded Parquet for large datasets
# ds_splits["train"].to_parquet("parquet/train/", batch_size=500)
# ds_splits["test"].to_parquet("parquet/test/", batch_size=500)