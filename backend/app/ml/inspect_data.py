import pandas as pd

#load the dataset
df= pd.read_csv("../../data/raw/reviews.csv")

print("\nShape of the dataset:", df.shape)
print("\nColumns in the dataset:", df.columns.to_list())
print("\nFirst 5 rows of the dataset:\n", df.head())
print("\nMissing values in each column:\n", df.isnull().sum())
