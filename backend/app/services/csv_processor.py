import pandas as pd


def process_uploaded_csv(file_path, ml_service):

    df = pd.read_csv(file_path)

    reviews = df["review"].tolist()

    results = []

    for review in reviews:
        result = ml_service.analyze_review(review)
        results.append(result)

    return {
        "total_reviews": len(results),
        "results": results[:10]
    }