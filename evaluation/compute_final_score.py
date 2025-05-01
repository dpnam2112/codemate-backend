import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import argparse

def truncate_id(path_id: str, method="head", head=6, tail=4) -> str:
    if method == "head":
        return path_id[:head]
    elif method == "head_tail":
        return f"{path_id[:head]}...{path_id[-tail:]}"
    else:
        raise ValueError("Unsupported truncate method")

# Metric weights
METRIC_WEIGHTS = {
    "Goal Alignment (GEval)": 0.4,
    "Explanation Quality (GEval)": 0.25,
    "Ordering Logic (GEval)": 0.2,
    "Module Appropriateness (GEval)": 0.15,
}

def compute_final_score(metric_rows):
    total_score = 0.0
    total_weight = 0.0
    for _, row in metric_rows.iterrows():
        metric = row["metric"]
        score = row["score"]
        if metric in METRIC_WEIGHTS:
            weight = METRIC_WEIGHTS[metric]
            total_score += weight * score
            total_weight += weight
    return round(total_score / total_weight, 4) if total_weight > 0 else 0.0

def plot_final_scores_from_csv(
    input_csv: str,
    output_path: str,
    plot_type: str = "bar"
):
    """
    Plot final scores from a CSV and save to destination.

    If the CSV does not contain 'final_score', it will compute it first.
    """
    df = pd.read_csv(input_csv)

    if "final_score" not in df.columns:
        print("[INFO] 'final_score' not found, computing from metric scores...")
        results = []
        grouped = df.groupby(["path_id", "model"])

        for (path_id, model), group in grouped:
            goal = group.iloc[0]["goal"] if "goal" in group.columns else ""
            final_score = compute_final_score(group)
            results.append({
                "path_id": path_id,
                "model": model,
                "goal": goal,
                "final_score": final_score
            })

        df = pd.DataFrame(results)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if plot_type == "bar":
        plt.figure(figsize=(12, 7))

        pivot_df = df.pivot_table(
            index="path_id", columns="model", values="final_score"
        )

        x = range(len(pivot_df))
        width = 0.15  # width of each bar
        num_models = len(pivot_df.columns)
        offsets = [(i - num_models/2) * width + width/2 for i in range(num_models)]

        for i, model in enumerate(pivot_df.columns):
            plt.bar(
                [xi + offsets[i] for xi in x],
                pivot_df[model],
                width=width,
                label=model
            )

        plt.xlabel("Learning Path ID")
        plt.ylabel("Final Score (0–1)")
        plt.title("Final Score per Learning Path by Model")
        short_labels = [truncate_id(idx, method="head_tail") for idx in pivot_df.index]
        plt.xticks(ticks=x, labels=short_labels, rotation=45, ha="right")
        plt.ylim(0, 1)
        plt.legend()
        plt.tight_layout()


    elif plot_type == "model_bar":
        plt.figure(figsize=(8, 5))
        model_means = df.groupby("model")["final_score"].mean()
        model_means.plot(kind="bar", color="skyblue")

        plt.ylabel("Average Final Score (0–1)")
        plt.title("Average Final Score per Model")
        plt.ylim(0, 1)
        plt.tight_layout()

    else:
        raise ValueError(f"Unsupported plot type: {plot_type}")

    plt.savefig(output_path)
    print(f"✅ Plot saved to {output_path}")
    plt.close()

def main():
    parser = argparse.ArgumentParser(description="Plot final scores from CSV and save to destination.")
    parser.add_argument("--input", "-i", required=True, help="Input CSV file path")
    parser.add_argument("--output", "-o", required=True, help="Destination output image file path (e.g., plots/final_scores.png)")
    parser.add_argument("--plot-type", "-pt", choices=["bar", "model_bar"], default="bar", help="Type of plot: 'bar' or 'model_bar'")

    args = parser.parse_args()

    plot_final_scores_from_csv(
        input_csv=args.input,
        output_path=args.output,
        plot_type=args.plot_type
    )

if __name__ == "__main__":
    main()

